#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PROITVSE — агент новостей об ИИ для Telegram-канала.
# Собирает новости из RSS, фильтрует, формирует дайджест и публикует 2 раза в день.
#
# Установка:  pip install feedparser requests
# Запуск:
#   export BOT_TOKEN="7123456789:AAHf..."   # токен от @BotFather
#   export CHAT_ID="-1001234567890"         # id канала
#   python proitvse_agent.py
#
# Опционально (суммаризация через ИИ, OpenAI-совместимый API):
#   export LLM_API_KEY="sk-..."
#   export LLM_BASE_URL="https://api.openai.com/v1"
#   export LLM_MODEL="gpt-4o-mini"
# Без ключа публикуется заголовок + ссылка (тоже рабочий вариант).
# Запуск 24/7: на VPS или домашнем ПК через systemd/screen.

import os, json, time, logging, random
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import requests

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHAT_ID     = os.environ["CHAT_ID"]
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL   = os.getenv("LLM_MODEL", "gpt-4o-mini")

POST_TIMES = ["09:00", "20:00"]          # время публикации (час:мин)
MAX_NEWS_PER_POST = 5                    # новостей в одном дайджесте
POSTED_DB = Path("posted_links.json")    # база опубликованных ссылок

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("proitvse")

# ---------- БАЗА ОПУБЛИКОВАННЫХ ----------
def load_posted():
    if POSTED_DB.exists():
        return set(json.loads(POSTED_DB.read_text(encoding="utf-8")))
    return set()

def save_posted(links):
    POSTED_DB.write_text(json.dumps(list(links), ensure_ascii=False), encoding="utf-8")

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
                summary = e.get("summary", "")[:500]
                if is_relevant(title, summary):
                    news.append({"title": title, "link": link, "summary": summary})
        except Exception as ex:
            log.warning("Ошибка ленты %s: %s", url, ex)
        time.sleep(1)
    random.shuffle(news)
    return news

# ---------- СУММАРИЗАЦИЯ (опционально) ----------
def summarize(title, summary):
    if not LLM_API_KEY:
        return ""
    try:
        r = requests.post(
            LLM_BASE_URL + "/chat/completions",
            headers={"Authorization": "Bearer " + LLM_API_KEY},
            json={
                "model": LLM_MODEL,
                "messages": [{
                    "role": "user",
                    "content": ("Перескажи новость об ИИ одним предложением на русском, "
                                "до 180 символов, без воды и кликбейта.\n\n"
                                "Заголовок: " + title + "\nТекст: " + summary[:1000])
                }],
                "max_tokens": 120, "temperature": 0.3,
            },
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as ex:
        log.warning("Суммаризация не удалась: %s", ex)
        return ""

# ---------- ПУБЛИКАЦИЯ ----------
def tg_post(text):
    r = requests.post(
        "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()
    log.info("Пост опубликован")

def build_post(news):
    now = datetime.now().strftime("%d.%m.%Y")
    period = "☀️ Утренний" if datetime.now().hour < 15 else "🌙 Вечерний"
    lines = [period + " дайджест AI-новостей | " + now + "\n"]
    for i, n in enumerate(news, 1):
        short = summarize(n["title"], n["summary"])
        lines.append(str(i) + ". <b>" + n["title"] + "</b>")
        if short:
            lines.append(short)
        lines.append("<a href=\"" + n["link"] + "\">Читать →</a>\n")
    lines.append("Подписывайся: @proitvse")
    return "\n".join(lines)

# ---------- РАСПИСАНИЕ ----------
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
    idx = 0
    while True:
        wait_until(POST_TIMES[idx % 2])
        posted = load_posted()
        fresh = [n for n in fetch_news() if n["link"] not in posted][:MAX_NEWS_PER_POST]
        if fresh:
            try:
                tg_post(build_post(fresh))
                posted.update(n["link"] for n in fresh)
                save_posted(posted)
            except Exception as ex:
                log.error("Ошибка публикации: %s", ex)
        else:
            log.info("Новых новостей нет — пропуск")
        idx += 1
