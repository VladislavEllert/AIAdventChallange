"""AI Advent #8 — Week 1, Day 1 (Telegram-обёртка).

Telegram-бот: принимает текст → шлёт в LLM через ProxyAPI → отвечает в чат.
Библиотека: python-telegram-bot (async).

Нужны два ключа в .env (корень репо):
    PROXYAPI_KEY=...
    TELEGRAM_BOT_TOKEN=...   # выдаёт @BotFather

Запуск:
    python bot.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

MODEL = "gemini/gemini-2.5-flash-lite"

SYSTEM_PROMPT = (
    "Ты — Telegram-бот по имени MyLittleGemeni, сделанный в рамках курса "
    "AI Advent Challenge #8. Работаешь поверх модели Google Gemini "
    "(gemini-2.5-flash-lite) через API ProxyAPI. Общаешься с пользователем "
    "в чате Telegram. Отвечай по-русски, кратко и по делу. Если спросят, кто "
    "ты — честно говори, что ты Telegram-бот на Gemini, а не сайт и не человек."
)

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("advent-bot")


def ask_llm(prompt: str) -> str:
    """Синхронный запрос к LLM. Вызывается в отдельном потоке (см. on_message)."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот курса AI Advent. Напиши вопрос — спрошу у нейросети "
        f"({MODEL}) и пришлю ответ."
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = update.message.text
    log.info("Запрос от %s: %s", update.effective_user.id, prompt)

    # "печатает..." пока ждём ответ
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # client.chat... блокирующий — уводим в поток, чтобы не вешать event loop
    try:
        answer = await asyncio.to_thread(ask_llm, prompt)
    except Exception as e:  # noqa: BLE001 — показываем любую ошибку в чат
        log.exception("Ошибка запроса к LLM")
        answer = f"Ошибка при запросе к нейросети: {e}"

    await update.message.reply_text(answer)


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    log.info("Бот запущен. Останов — Ctrl+C.")
    app.run_polling()


if __name__ == "__main__":
    main()
