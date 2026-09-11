# PROITVSE — Telegram-канал новостей об ИИ 🤖

Автоматический агент: собирает новости об искусственном интеллекте из RSS-источников,
формирует дайджест и публикует его в Telegram-канал **2 раза в день** (09:00 и 20:00 МСК).

## Возможности

- 📡 Сбор новостей из 7 источников: OpenAI, Anthropic, Google AI, Hugging Face, Хабр, Reddit
- 🎯 Фильтрация по ключевым словам + отсечение шума (крипто и т.п.)
- 🚫 Защита от дублей (база опубликованных ссылок)
- ✍️ Опциональная суммаризация новостей через LLM (OpenAI-совместимый API, например Kimi)
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
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates` — значение `"chat":{"id":-100...}`

## Запуск 24/7 — Вариант А: GitHub Actions (рекомендуется, сервер не нужен) ☁️

Агент запускается бесплатно на инфраструктуре GitHub по расписанию 09:00 и 20:00 МСК.

1. Добавьте в репозиторий файл `.github/workflows/digest.yml` (лежит рядом с этим README
   в архиве/чате либо создайте через **Add file → Create new file** с именем
   `.github/workflows/digest.yml` и вставьте содержимое).
2. Откройте репозиторий → **Settings → Secrets and variables → Actions → New repository secret**
3. Добавьте секреты:
   - `BOT_TOKEN` — токен бота от @BotFather
   - `CHAT_ID` — id канала (вида `-100...`)
   - *(опционально)* `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — для умных пересказов.
     Например для Kimi: `LLM_BASE_URL=https://api.moonshot.ai/v1`, `LLM_MODEL=kimi-k2-0711-preview`
4. Готово — workflow сработает по расписанию. Проверить вручную:
   вкладка **Actions → PROITVSE digest → Run workflow**.

Как это работает: каждый запуск выполняет `python proitvse_agent.py --once` — собирает новости,
публикует дайджест и коммитит обновлённую базу `posted_links.json` обратно в репозиторий
(поэтому дубли исключены даже без своего сервера).

> Примечание: GitHub может запускать scheduled-задачи с задержкой в несколько минут —
> для новостного канала это некритично.

## Запуск 24/7 — Вариант Б: свой сервер (systemd, Linux)

1. Установите московское время (агент публикует по локальному времени сервера):
   ```bash
   sudo timedatectl set-timezone Europe/Moscow
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

python proitvse_agent.py --once   # один дайджест сразу
python proitvse_agent.py          # режим демона с расписанием POST_TIMES
```

Без `LLM_API_KEY` публикуется заголовок + ссылка — тоже рабочий вариант.

## Настройка (в начале proitvse_agent.py)

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `POST_TIMES` | `["09:00", "20:00"]` | Время публикаций (только режим демона; в GitHub Actions расписание в `.github/workflows/digest.yml`) |
| `MAX_NEWS_PER_POST` | `5` | Новостей в дайджесте |
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
