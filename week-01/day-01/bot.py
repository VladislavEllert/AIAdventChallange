import asyncio
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

MODELS = [
    ("gemini/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite ⚡", "26/129₽"),
    ("gemini/gemini-2.5-flash", "Gemini 2.5 Flash", "78/645₽"),
    ("openai/gpt-4o-mini", "GPT-4o mini", "39/155₽"),
    ("openai/gpt-4.1-mini", "GPT-4.1 mini", "104/413₽"),
    ("openai/gpt-4.1-nano", "GPT-4.1 nano", "26/104₽"),
    ("openai/gpt-5-nano", "GPT-5 nano", "13/104₽"),
    ("openai/gpt-3.5-turbo", "GPT-3.5 Turbo", "129/387₽"),
]
DEFAULT_MODEL = MODELS[0][0]
LABELS = {model_id: label for model_id, label, _ in MODELS}

SYSTEM_PROMPT = (
    "Ты — Telegram-бот MyLittleGemeni, сделанный в рамках курса AI Advent "
    "Challenge #8. Работаешь через API ProxyAPI на модели, которую выбрал "
    "пользователь. Отвечай по-русски, кратко и по делу. Если спросят, кто "
    "ты — честно говори, что ты Telegram-бот, а не сайт и не человек."
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


def ask_llm(prompt: str, model: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def current_model(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("model", DEFAULT_MODEL)


def model_keyboard(current: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            ("✅ " if model_id == current else "") + f"{label} ({price})",
            callback_data=model_id,
        )]
        for model_id, label, price in MODELS
    ]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот курса AI Advent. Пиши вопрос — отвечу через выбранную модель.\n\n"
        f"Текущая модель: {LABELS[current_model(context)]}\n"
        "Сменить модель: /model"
    )


async def choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Выбери модель, с которой будешь общаться.\n"
        "В скобках — цена: вход/выход ₽ за 1 млн токенов.",
        reply_markup=model_keyboard(current_model(context)),
    )


async def on_model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    model = query.data
    context.user_data["model"] = model
    await query.edit_message_text(f"Готово. Теперь общаешься с: {LABELS.get(model, model)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = update.message.text
    model = current_model(context)
    log.info("Запрос от %s [%s]: %s", update.effective_user.id, model, prompt)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        answer = await asyncio.to_thread(ask_llm, prompt, model)
    except Exception as e:
        log.exception("Ошибка запроса к LLM")
        answer = f"Ошибка при запросе к нейросети: {e}"

    await update.message.reply_text(answer)


async def setup_commands(app: Application) -> None:
    await app.bot.set_my_commands([
        ("start", "Запуск и текущая модель"),
        ("model", "Выбрать модель"),
    ])


def main() -> None:
    app = (
        Application.builder()
        .token(os.environ["TELEGRAM_BOT_TOKEN"])
        .post_init(setup_commands)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("model", choose_model))
    app.add_handler(CallbackQueryHandler(on_model_selected))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
