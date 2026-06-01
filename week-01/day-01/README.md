# Неделя 1 — День 1

## Задание

Минимальный код, который шлёт запрос в LLM через API (**ProxyAPI**),
получает ответ и выводит его. Сдаём в виде **Telegram-бота** (удобно
демонстрировать в видео).

## Формат сдачи

**Видео + код. Видео важнее кода.**

## Что внутри

- `bot.py` — Telegram-бот (основной вариант сдачи): текст → LLM → ответ в чат.
- `main.py` — минимальный CLI (тот же запрос в консоль, для проверки API).

## Технические детали

- API: ProxyAPI, OpenAI-совместимый. base_url `https://openai.api.proxyapi.ru/v1`.
- Модель: `gemini-2.5-flash-lite`.
- Telegram: библиотека `python-telegram-bot` (async).
- Ключи в `.env` (корень репо): `PROXYAPI_KEY`, `TELEGRAM_BOT_TOKEN`.

## Установка

```bash
cd week-01/day-01
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# в корне репо: скопируй .env.example -> .env и впиши оба ключа
```

## Запуск

```bash
python bot.py      # Telegram-бот
python main.py     # либо просто CLI-проверка API
```

## Что сделать в Telegram (на твоей стороне)

1. Открой **@BotFather** в Telegram.
2. `/newbot` → задай имя бота и username (должен кончаться на `bot`).
3. BotFather пришлёт **token** — впиши его в `.env` как `TELEGRAM_BOT_TOKEN`.
4. Запусти `python bot.py`.
5. Открой своего бота по ссылке от BotFather → `/start` → пиши вопросы.

## Статус

`todo` — код написан, ждёт ключи (ProxyAPI + BotFather) для запуска и видео.
