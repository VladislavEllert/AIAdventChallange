# Неделя 1 — День 1

## Задание

Минимальный код, который шлёт запрос в LLM через API (**ProxyAPI**),
получает ответ и выводит его. Сдаём в виде **Telegram-бота** (удобно
демонстрировать в видео).

## Формат сдачи

**Видео + код. Видео важнее кода.**

## Что внутри

- `bot.py` — Telegram-бот: текст → LLM → ответ в чат.
  - `/model` — кнопки выбора модели (лёгкие Gemini + GPT). Выбор хранится
    per-user, его сообщения идут в выбранную модель. Список — в `MODELS`.

## Технические детали

- API: ProxyAPI, OpenAI-совместимый. base_url `https://openai.api.proxyapi.ru/v1`.
- Модель: `gemini/gemini-2.5-flash-lite` (с префиксом `gemini/` — иначе 400).
  Проверено вживую. `gemini-3.1-flash-lite` через ProxyAPI не работает.
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
python bot.py
```

## Что сделать в Telegram (на твоей стороне)

1. Открой **@BotFather** в Telegram.
2. `/newbot` → задай имя бота и username (должен кончаться на `bot`).
3. BotFather пришлёт **token** → впиши его в `.env` как `TELEGRAM_BOT_TOKEN`.
4. Запусти `python bot.py`.
5. Открой своего бота по ссылке от BotFather → `/start` → пиши вопросы.

## Статус

`done` — бот работает вживую, задание выполнено.
