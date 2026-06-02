import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "openai/gpt-4o-mini"

SYSTEM_B = (
    "Отвечай строго в таком формате: ровно 3 пункта, каждый с новой строки "
    "и начинается с '— '. Каждый пункт не длиннее 10 слов. Без вступления и "
    "заключения. После последнего пункта напиши маркер [КОНЕЦ]."
)
MAX_TOKENS_B = 150
STOP_B = ["[КОНЕЦ]"]

MAX_TOKENS_C = 20

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)


def run(messages, **params):
    response = client.chat.completions.create(model=MODEL, messages=messages, **params)
    return response.choices[0].message.content, response.usage


def print_block(title, text, usage):
    print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")
    print(text.strip())
    print(
        f"\n[токены — вход: {usage.prompt_tokens}, выход: {usage.completion_tokens}, "
        f"всего: {usage.total_tokens}]"
    )


def main():
    prompt = input("Вопрос: ").strip()

    text_a, usage_a = run([{"role": "user", "content": prompt}])
    print_block("A: без ограничений", text_a, usage_a)

    text_b, usage_b = run(
        [
            {"role": "system", "content": SYSTEM_B},
            {"role": "user", "content": prompt},
        ],
        max_tokens=MAX_TOKENS_B,
        stop=STOP_B,
    )
    print_block("B: с ограничениями (формат + длина + stop)", text_b, usage_b)

    text_c, usage_c = run([{"role": "user", "content": prompt}], max_tokens=MAX_TOKENS_C)
    print_block("C: тупой обрыв (max_tokens=20, без формата)", text_c, usage_c)

    print(f"\n{'=' * 50}\nСводка выходных токенов\n{'=' * 50}")
    print(f"A без ограничений:  {usage_a.completion_tokens}")
    print(f"B умный stop:       {usage_b.completion_tokens}")
    print(f"C гильотина 20:     {usage_c.completion_tokens}")


if __name__ == "__main__":
    main()
