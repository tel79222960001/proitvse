# PROITVSE — Telegram-канал новостей об ИИ 🤖

Автоматический агент: собирает новости об искусственном интеллекте из RSS-источников,
формирует дайджест и публикует его в Telegram-канал **2 раза в день** (09:00 и 20:00).

## Возможности

- 📡 Сбор новостей из 7 источников: OpenAI, Anthropic, Google AI, Hugging Face, Хабр, Reddit
- 🎯 Фильтрация по ключевым словам + отсечение шума (крипто и т.п.)
- 🚫 Защита от дублей (база опубликованных ссылок)
- ✍️ Опциональная суммаризация новостей через LLM (OpenAI-совместимый API)
- 📮 Публикация по расписанию, переживает перезапуск (база дублей на диске)

## Установка

```bash
pip install feedparser requests
```

## Настройка

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен
2. Добавьте бота в канал как **администратора** с правом публикации
3. Узнайте `chat_id` канала: напишите в канал сообщение, затем откройте
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates` — значение `"chat":{"id":-100...}`

## Запуск

```bash
export BOT_TOKEN="7123456789:AAHf..."      # токен бота
export CHAT_ID="-1001234567890"            # id канала

# опционально — умные пересказы новостей:
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o-mini"

python proitvse_agent.py
```

Без `LLM_API_KEY` публикуется заголовок + ссылка — тоже рабочий вариант.

## Запуск 24/7 (systemd, Linux)

Создайте файл `/etc/systemd/system/proitvse.service`:

```ini
[Unit]
Description=PROITVSE AI news agent
After=network.target

[Service]
WorkingDirectory=/opt/proitvse
Environment=BOT_TOKEN=ваш_токен
Environment=CHAT_ID=-100xxxxxxxxxx
Environment=LLM_API_KEY=sk-...
ExecStart=/usr/bin/python3 /opt/proitvse/proitvse_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now proitvse
sudo systemctl status proitvse   # проверка
journalctl -u proitvse -f        # логи
```

## Настройка (в начале proitvse_agent.py)

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `POST_TIMES` | `["09:00", "20:00"]` | Время публикаций |
| `MAX_NEWS_PER_POST` | `5` | Новостей в дайджесте |
| `RSS_SOURCES` | 7 лент | Источники новостей |
| `KEYWORDS` / `STOPWORDS` | — | Фильтры тем |

## Структура

```
proitvse_agent.py   # весь агент в одном файле
posted_links.json   # создаётся автоматически: база опубликованных ссылок
```

## Планы / Roadmap

- [ ] Поддержка новостей с картинками
- [ ] Тематические рубрики (модели / инструменты / бизнес)
- [ ] Статистика охватов
- [ ] Монетизация: Telegram Ads revenue share, партнёрки

---

Канал: [@proitvse](https://t.me/proitvse)
