"""День 4 — температура.

Два прогона одного промпта по температурам [0..2]:
  python temperature.py        — дефолтные top_p/top_k → разница только от температуры
  python temperature.py max    — top_p=1.0 + top_k=1000 → сняты фильтры хвоста, распад
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gemini/gemini-2.5-flash-lite"
TEMPERATURES = [0, 0.7, 1.2, 1.5, 2.0]
MAX_TOKENS = 300

# параметры режима "max" (сходит с ума)
TOP_P_MAX = 1.0   # не отсекаем хвост по массе
TOP_K_MAX = 1000  # не режем пул по числу кандидатов (Gemini, через extra_body)


PROMPT = "Сочини стихотворение про то, как Таня уронила в речку мячик."

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)


def ask(temperature, crank):
    kwargs = dict(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=temperature,
        max_tokens=MAX_TOKENS,
    )
    if crank:  # режим max — снимаем top_p и top_k
        kwargs["top_p"] = TOP_P_MAX
        kwargs["extra_body"] = {"top_k": TOP_K_MAX}
    response = client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "<пустой ответ>").strip()


def main():
    crank = len(sys.argv) > 1 and sys.argv[1] == "max"
    mode = "max (top_p=1.0, top_k=1000)" if crank else "дефолтные top_p/top_k"

    print(f"Модель: {MODEL} | режим: {mode}")
    print(f"Промпт: {PROMPT}")

    for temp in TEMPERATURES:
        print(f"\n{'=' * 60}\ntemperature = {temp}\n{'=' * 60}")
        print(ask(temp, crank))


if __name__ == "__main__":
    main()
