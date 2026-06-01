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
    "Ты — Telegram-бот по имени MyLittleGemeni, созданный в рамках курса "
    "AI Advent Challenge #8. Работаешь поверх модели Google Gemini "
    "(gemini-2.5-flash-lite) через API ProxyAPI. Общаешься с пользователем "
    "в чате Telegram. Отвечай по-русски, кратко и по делу. Если спросят, кто "
    "ты — честно говори, что ты Telegram-бот на Gemini, а не сайт и не человек."
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("advent-bot")

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)


def ask_llm(prompt: str) -> str:
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
        "Привет! Я бот курса AI Advent на модели Gemini. "
        "Напиши вопрос — пришлю ответ."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = update.message.text
    log.info("Запрос от %s: %s", update.effective_user.id, prompt)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        answer = await asyncio.to_thread(ask_llm, prompt)
    except Exception as e:
        log.exception("Ошибка запроса к LLM")
        answer = f"Ошибка при запросе к нейросети: {e}"

    await update.message.reply_text(answer)


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
