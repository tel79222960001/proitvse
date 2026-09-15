# PROITVSE — Telegram-канал новостей об ИИ 🤖

Автоматический агент: собирает новости об искусственном интеллекте из RSS-источников
и публикует **2 поста в день** (09:00 и 18:00 по Екатеринбургу, UTC+5).

**Формат каждого поста — одна новость:**
📝 выдержка из источника (до 10 предложений) · 🎯 основной тезис · 💡 вывод (1–2 предложения) · 🔗 ссылка на источник

Англоязычные источники (OpenAI, Anthropic, Google AI, Hugging Face, Reddit) **публикуются на русском**:
агент автоматически определяет язык и переводит заголовок и выдержку (🌐 *Автоперевод с английского*).

## Возможности

- 📡 Сбор новостей из 7 источников: OpenAI, Anthropic, Google AI, Hugging Face, Хабр, Reddit
- 🌐 Автоматический перевод англоязычных статей на русский: сначала через LLM (тот же `LLM_API_KEY`,
  что и для тезисов), без ключа — через бесплатный MyMemory; если перевод недоступен — пост помечается
  и публикуется оригинал
- 🎯 Фильтрация по ключевым словам + отсечение шума (крипто и т.п.)
- 🚫 Защита от дублей (база опубликованных ссылок)
- ✍️ Опционально: тезис и вывод генерируются LLM (OpenAI-совместимый API, например Kimi)
- 📮 Публикация по расписанию, переживает перезапуск (база дублей на диске)
- ☁️ Два режима 24/7: GitHub Actions (без сервера) или systemd на своём VPS/ПК

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен
2. Добавьте бота в канал как **администратора** с правом публикации
3. Узнайте `chat_id` канала: напишите в канал сообщение, затем откройте
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates` — значение `"chat":{"id":-100...`

## Запуск 24/7 — Вариант А: GitHub Actions (рекомендуется, сервер не нужен) ☁️

Агент запускается бесплатно на инфраструктуре GitHub по расписанию 09:00 и 18:00 по Екатеринбургу.

1. Файл `.github/workflows/digest.yml` лежит в репозитории.
2. Откройте репозиторий → **Settings → Secrets and variables → Actions → New repository secret**
3. Добавьте секреты:
   - `BOT_TOKEN` — токен бота от @BotFather
   - `CHAT_ID` — id канала (вида `-100...`)
   - *(опционально)* `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — для тезисов, выводов и перевода.
     Например для Kimi: `LLM_BASE_URL=https://api.moonshot.ai/v1`, `LLM_MODEL=kimi-k2-0711-preview`
4. Готово — workflow сработает по расписанию. Проверить вручную:
   вкладка **Actions → PROITVSE digest → Run workflow**.

Как это работает: каждый запуск выполняет `python proitvse_agent.py --once` — берёт следующую
свежую новость, публикует пост и коммитит обновлённую базу `posted_links.json` обратно
в репозиторий (поэтому дубли исключены даже без своего сервера). Два запуска в день = два поста.

> Примечание: GitHub может запускать scheduled-задачи с задержкой в несколько минут —
> для новостного канала это некритично.

## Запуск 24/7 — Вариант Б: свой сервер (systemd, Linux)

1. Установите екатеринбургское время (агент публикует по локальному времени сервера):
   ```bash
   sudo timedatectl set-timezone Asia/Yekaterinburg
   ```
2. Скопируйте проект в `/opt/proitvse`, создайте файл `/etc/systemd/system/proitvse.service`:

```ini
[Unit]
Description=PROITVSE AI news agent
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/proitvse
Environment=BOT_TOKEN=ваш_токен
Environment=CHAT_ID=-100xxxxxxxxxx
# опционально:
# Environment=LLM_API_KEY=sk-...
# Environment=LLM_BASE_URL=https://api.moonshot.ai/v1
# Environment=LLM_MODEL=kimi-k2-0711-preview
ExecStart=/usr/bin/python3 /opt/proitvse/proitvse_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now proitvse
sudo systemctl status proitvse   # проверка
journalctl -u proitvse -f        # логи
```

## Локальный запуск (для теста)

```bash
export BOT_TOKEN="7123456789:AAHf..."      # токен бота
export CHAT_ID="-1001234567890"            # id канала

python proitvse_agent.py --once   # один пост сразу
python proitvse_agent.py          # режим демона с расписанием POST_TIMES
```

Без `LLM_API_KEY` публикуется выдержка + ссылка (тезис и вывод пропускаются) — тоже рабочий вариант.
Перевод англоязычных источников при этом работает через бесплатный MyMemory (лимит ~5000 символов в день);
при исчерпании лимита пост выйдет на английском с пометкой.

## Настройка (в начале proitvse_agent.py)

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `POST_TIMES` | `["09:00", "18:00"]` | Время публикаций (только режим демона; в GitHub Actions расписание в `.github/workflows/digest.yml`) |
| `MAX_SENTENCES` | `10` | Предложений в выдержке из источника |
| `RSS_SOURCES` | 7 лент | Источники новостей |
| `KEYWORDS` / `STOPWORDS` | — | Фильтры тем |

## Структура

```
proitvse_agent.py            # весь агент в одном файле
requirements.txt             # зависимости (feedparser, requests)
.github/workflows/digest.yml # запуск 24/7 через GitHub Actions
posted_links.json            # создаётся автоматически: база опубликованных ссылок
```

## Планы / Roadmap

- [ ] Поддержка новостей с картинками
- [ ] Тематические рубрики (модели / инструменты / бизнес)
- [ ] Статистика охватов
- [ ] Монетизация: Telegram Ads revenue share, партнёрки

---

Канал: [@proitvse](https://t.me/proitvse)
