#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PROITVSE — агент новостей об ИИ для Telegram-канала.
# Публикует ОДНУ новость за запуск: выдержка из источника (до 10 предложений),
# основной тезис, краткий вывод и ссылка. 2 поста в день: 09:00 и 18:00 по Екатеринбургу (UTC+5).
#
# Установка:  pip install -r requirements.txt
#
# Режим 1 — постоянная работа (systemd/screen на своём сервере):
#   export BOT_TOKEN="7123456789:AAHf..."   # токен от @BotFather
#   export CHAT_ID="-1001234567890"         # id канала
#   python proitvse_agent.py
#
# Режим 2 — одноразовый запуск (GitHub Actions / cron):
#   python proitvse_agent.py --once
#
# Опционально (тезис и вывод через ИИ, OpenAI-совместимый API, например Kimi):
#   export LLM_API_KEY="sk-..."
#   export LLM_BASE_URL="https://api.moonshot.ai/v1"
#   export LLM_MODEL="kimi-k2-0711-preview"
# Без ключа публикуется выдержка + ссылка (тоже рабочий вариант).

import os, sys, re, json, time, logging, random, html as html_mod
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import requests

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHAT_ID     = os.environ["CHAT_ID"]
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.moonshot.ai/v1")
LLM_MODEL   = os.getenv("LLM_MODEL", "kimi-k2-0711-preview")

POST_TIMES = ["09:00", "18:00"]   # 2 поста в день, время Екатеринбург (UTC+5, только режим демона)
MAX_SENTENCES = 10                        # предложений в выдержке из источника
POSTED_DB = Path("posted_links.json")     # база опубликованных ссылок

RSS_SOURCES = [
    "https://openai.com/news/rss.xml",
    "https://www.anthropic.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://huggingface.co/blog/feed.xml",
    "https://habr.com/ru/rss/search/?q=%D0%BD%D0%B5%D0%B9%D1%80%D0%BE%D1%81%D0%B5%D1%82%D0%B8&target_type=posts&order=date",
    "https://www.reddit.com/r/MachineLearning/.rss",
    "https://www.reddit.com/r/LocalLLaMA/.rss",
]

KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpt",
    "claude", "gemini", "нейросет", "искусственн", "машинн обучен",
    "generative", "multimodal", "diffusion", "transformer", "agents",
    "open source model", "inference", "fine-tun", "датасет",
]

STOPWORDS = ["crypto", "nft", "bitcoin", "крипт", "биткоин"]

EMOJIS = ["🤖", "🧠", "⚡", "🚀", "🔥", "💡", "🦾", "📡"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("proitvse")

# ---------- БАЗА ОПУБЛИКОВАННЫХ ----------
def load_posted():
    if POSTED_DB.exists():
        try:
            return set(json.loads(POSTED_DB.read_text(encoding="utf-8")))
        except Exception as ex:
            log.warning("База ссылок повреждена, начинаю с пустой: %s", ex)
            return set()
    return set()

def save_posted(links):
    tmp = POSTED_DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(list(links), ensure_ascii=False), encoding="utf-8")
    tmp.replace(POSTED_DB)

# ---------- СБОР НОВОСТЕЙ ----------
def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()
    if any(w in text for w in STOPWORDS):
        return False
    return any(k in text for k in KEYWORDS)

def fetch_news():
    news, seen = [], set()
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:10]:
                link = getattr(e, "link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                title = e.get("title", "").strip()
                summary = e.get("summary", "")[:2000]
                if is_relevant(title, summary):
                    news.append({"title": title, "link": link, "summary": summary})
        except Exception as ex:
            log.warning("Ошибка ленты %s: %s", url, ex)
        time.sleep(1)
    random.shuffle(news)
    return news

# ---------- ТЕКСТ: ВЫДЕРЖКА, ТЕЗИС, ВЫВОД ----------
def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html_mod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def excerpt_of(summary, max_sentences=MAX_SENTENCES):
    """Выдержка из источника: чистый текст, до max_sentences предложений."""
    text = strip_html(summary)
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?\u2026])\s+", text)
    return " ".join(sentences[:max_sentences]).strip()

def analyze(title, excerpt):
    """LLM: основной тезис (1 предложение) и вывод (1-2 предложения).
    Возвращает (тезис, вывод). Без ключа — пустые строки."""
    if not LLM_API_KEY or not excerpt:
        return "", ""
    try:
        r = requests.post(
            LLM_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + LLM_API_KEY},
            json={
                "model": LLM_MODEL,
                "messages": [{
                    "role": "user",
                    "content": ("Новость: " + title +
                                "\n\nТекст: " + excerpt[:2500] +
                                "\n\nОтветь строго двумя строками без лишнего:\n"
                                "ТЕЗИС: одно предложение — главная суть новости\n"
                                "ВЫВОД: одно-два предложения — почему это важно для рынка ИИ")
                }],
                "max_tokens": 250, "temperature": 0.3,
            },
            timeout=40,
        )
        text = r.json()["choices"][0]["message"]["content"].strip()
        thesis, conclusion = "", ""
        for line in text.splitlines():
            if line.upper().startswith("ТЕЗИС:"):
                thesis = line.split(":", 1)[1].strip()
            elif line.upper().startswith("ВЫВОД:"):
                conclusion = line.split(":", 1)[1].strip()
        return thesis, conclusion
    except Exception as ex:
        log.warning("Анализ LLM не удался: %s", ex)
        return "", ""

# ---------- ПУБЛИКАЦИЯ ----------
def tg_post(text):
    r = requests.post(
        "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
              "disable_web_page_preview": False},
        timeout=30,
    )
    r.raise_for_status()
    log.info("Пост опубликован")

def build_post(news):
    """Один пост = одна новость: заголовок, выдержка, тезис, вывод, ссылка."""
    title, link, summary = news["title"], news["link"], news["summary"]
    excerpt = excerpt_of(summary)
    thesis, conclusion = analyze(title, excerpt)

    lines = [random.choice(EMOJIS) + " <b>" + title + "</b>", ""]
    if excerpt:
        lines.append("📝 <i>Выдержка из источника:</i>")
        lines.append(excerpt)
        lines.append("")
    if thesis:
        lines.append("🎯 <b>Тезис:</b> " + thesis)
    if conclusion:
        lines.append("💡 <b>Вывод:</b> " + conclusion)
    if thesis or conclusion:
        lines.append("")
    lines.append('<a href="' + link + '">🔗 Источник</a>')
    lines.append("")
    lines.append("Подписывайся: @proitvse")

    text = "\n".join(lines)
    # лимит Telegram — 4096 символов; ужимаем выдержку, если не влезает
    while len(text) > 4000 and " " in excerpt:
        parts = excerpt.rsplit(" ", 1)
        excerpt = parts[0]
        lines[2] = excerpt + " …"
        text = "\n".join(lines)
    return text

def publish_next():
    """Опубликовать следующую свежую новость. True — пост вышел."""
    posted = load_posted()
    fresh = [n for n in fetch_news() if n["link"] not in posted]
    if not fresh:
        log.info("Новых новостей нет — пропуск")
        return False
    news = fresh[0]
    tg_post(build_post(news))
    posted.add(news["link"])
    save_posted(posted)
    return True

# ---------- РАСПИСАНИЕ (режим демона) ----------
def wait_until(hhmm):
    hh, mm = map(int, hhmm.split(":"))
    now = datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    sleep_s = (target - now).total_seconds()
    log.info("Следующий пост в %s (через %d ч)", hhmm, int(sleep_s // 3600))
    time.sleep(sleep_s)

if __name__ == "__main__":
    log.info("PROITVSE agent запущен")

    if "--once" in sys.argv:
        try:
            publish_next()
        except Exception as ex:
            log.error("Ошибка публикации: %s", ex)
            sys.exit(1)
        sys.exit(0)

    idx = 0
    while True:
        wait_until(POST_TIMES[idx % len(POST_TIMES)])
        try:
            publish_next()
        except Exception as ex:
            log.error("Ошибка публикации: %s", ex)
        idx += 1
