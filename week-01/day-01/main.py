"""AI Advent #8 — Week 1, Day 1.

Минимальный CLI: шлёт запрос в LLM через ProxyAPI (OpenAI-совместимый
эндпоинт), получает ответ и выводит в консоль.

Под задачу недели добавлены флаги для «дёргания» параметров модели:
temperature, top-p, top-k, max-tokens, seed, system-промпт.

Запуск:
    python main.py "Привет, кто ты?"
    python main.py "Напиши хайку про код" --temperature 1.0
    python main.py "2+2?" --temperature 0 --max-tokens 50
    echo "Объясни рекурсию" | python main.py        # промпт из stdin
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# Единый base_url ProxyAPI; роутинг по имени модели.
BASE_URL = "https://openai.api.proxyapi.ru/v1"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Минимальный запрос к LLM через ProxyAPI (OpenAI-совместимый API)."
    )
    p.add_argument(
        "prompt",
        nargs="*",
        help="Текст промпта. Если не задан — читается из stdin.",
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Имя модели (по умолч. {DEFAULT_MODEL}).")
    p.add_argument("--system", default=None, help="System-промпт (роль/настройка модели).")
    p.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="0 = точно/сухо, 1 = разброс/творчество. По умолч. 0.7.",
    )
    p.add_argument("--top-p", type=float, default=None, help="Nucleus sampling, порог 0..1.")
    p.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Берём только N кандидатов. Прокидывается через extra_body; "
        "Gemini-роут может проигнорировать.",
    )
    p.add_argument("--max-tokens", type=int, default=None, help="Лимит токенов ответа.")
    p.add_argument("--seed", type=int, default=None, help="Зерно рандома (управляемая недетерминированность).")
    return p.parse_args()


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return " ".join(args.prompt)
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    sys.exit("Ошибка: не передан промпт. Пример: python main.py \"Привет\"")


def build_messages(prompt: str, system: str | None) -> list[dict]:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def main() -> None:
    load_dotenv()
    api_key = os.getenv("PROXYAPI_KEY")
    if not api_key:
        sys.exit("Ошибка: нет PROXYAPI_KEY. Скопируй .env.example в .env и впиши ключ.")

    args = parse_args()
    prompt = read_prompt(args)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    # Собираем только заданные параметры — лишние None не шлём.
    params: dict = {
        "model": args.model,
        "messages": build_messages(prompt, args.system),
        "temperature": args.temperature,
    }
    if args.top_p is not None:
        params["top_p"] = args.top_p
    if args.max_tokens is not None:
        params["max_tokens"] = args.max_tokens
    if args.seed is not None:
        params["seed"] = args.seed
    if args.top_k is not None:
        # top_k не входит в OpenAI chat API — прокидываем как доп. поле.
        params["extra_body"] = {"top_k": args.top_k}

    try:
        resp = client.chat.completions.create(**params)
    except OpenAIError as e:
        sys.exit(f"Ошибка API: {e}")

    print(resp.choices[0].message.content)

    usage = resp.usage
    if usage is not None:
        print(
            f"\n[модель: {resp.model} | токены: "
            f"вход {usage.prompt_tokens}, выход {usage.completion_tokens}, "
            f"всего {usage.total_tokens}]",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
