"""День 5 — версии моделей.

Один и тот же промпт-ловушка (автомойка из day-03) прогоняется на четырёх
моделях GPT разного уровня и замеряются: время ответа, токены, стоимость.

  слабая/старая   → gpt-3.5-turbo
  средняя         → gpt-4o
  сильная обычная → gpt-4.1
  думающая        → o3 (reasoning-серия, тратит скрытые reasoning-токены)

Запуск:
  python model_versions.py
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Ловушка из day-03. Правильный ответ — ЕХАТЬ: машину надо помыть НА мойке,
# пешком придёшь без машины и мыть будет нечего. Слабая модель цепляется за
# "50 метров → пешком", сильная/думающая ловит подвох.
PROMPT = (
    "Мне нужно помыть машину, автомойка в 50 метрах от меня. "
    "Как мне лучше добраться до автомойки — доехать на машине, или дойти пешком?"
)
CORRECT = "ехать"

# Цены ProxyAPI, ₽ за 1M токенов (in / out).
# Источник: https://proxyapi.ru/pricing/list — сверено 2026-06-06.
# Прайс меняется, перед сдачей перепроверить живьём.
MODELS = [
    {"id": "openai/gpt-3.5-turbo", "tier": "слабая/старая",   "reasoning": False, "in": 129, "out": 387},
    {"id": "openai/gpt-4o",        "tier": "средняя",         "reasoning": False, "in": 645, "out": 2577},
    {"id": "openai/gpt-4.1",       "tier": "сильная обычная", "reasoning": False, "in": 516, "out": 2062},
    {"id": "openai/o3",            "tier": "думающая",        "reasoning": True,  "in": 607, "out": 1685},
]

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)


def ask(model):
    """Один вызов модели + сбор метрик. Возвращает dict с ответом и замерами."""
    kwargs = dict(
        model=model["id"],
        messages=[{"role": "user", "content": PROMPT}],
    )
    if model["reasoning"]:
        # o-серия: temperature не принимает (только дефолт), лимит — другой ключ.
        # Запас большой: reasoning-токены едят бюджет ДО финального ответа.
        kwargs["max_completion_tokens"] = 3000
    else:
        kwargs["temperature"] = 0          # детерминизм: разница от модели, не от рандома
        kwargs["max_tokens"] = 700

    t0 = time.perf_counter()
    resp = client.chat.completions.create(**kwargs)
    latency = time.perf_counter() - t0

    u = resp.usage
    # reasoning-токены лежат в деталях completion (есть только у o-серии)
    reasoning_tok = 0
    details = getattr(u, "completion_tokens_details", None)
    if details is not None:
        reasoning_tok = getattr(details, "reasoning_tokens", 0) or 0

    cost = (u.prompt_tokens * model["in"] + u.completion_tokens * model["out"]) / 1_000_000
    throughput = u.completion_tokens / latency if latency else 0

    return {
        "answer": (resp.choices[0].message.content or "<пустой ответ>").strip(),
        "latency": latency,
        "prompt_tok": u.prompt_tokens,
        "completion_tok": u.completion_tokens,
        "reasoning_tok": reasoning_tok,
        "total_tok": u.total_tokens,
        "cost": cost,
        "throughput": throughput,
    }


def main():
    print(f"Промпт-ловушка:\n{PROMPT}")
    print(f"\nПравильный ответ: {CORRECT.upper()}\n")

    rows = []
    for m in MODELS:
        print(f"\n{'=' * 70}\n{m['tier'].upper()}  —  {m['id']}\n{'=' * 70}")
        try:
            r = ask(m)
        except Exception as e:  # одна модель упала — не валим весь прогон
            print(f"ОШИБКА: {e}")
            continue
        print(r["answer"])
        print(
            f"\n  latency: {r['latency']:.2f} c"
            f" | токены in/out: {r['prompt_tok']}/{r['completion_tok']}"
            + (f" (из них reasoning: {r['reasoning_tok']})" if r["reasoning_tok"] else "")
            + f" | total: {r['total_tok']}"
            f" | throughput: {r['throughput']:.1f} ток/с"
            f" | стоимость: {r['cost']:.4f} ₽"
        )
        rows.append((m, r))

    # --- сводная таблица ---
    print(f"\n\n{'=' * 70}\nСВОДКА\n{'=' * 70}")
    head = f"{'модель':<22}{'latency':>9}{'in/out':>12}{'reason':>8}{'ток/с':>9}{'₽':>10}"
    print(head)
    print("-" * len(head))
    for m, r in rows:
        io = f"{r['prompt_tok']}/{r['completion_tok']}"
        print(
            f"{m['id'].replace('openai/', ''):<22}"
            f"{r['latency']:>8.2f}c"
            f"{io:>12}"
            f"{r['reasoning_tok']:>8}"
            f"{r['throughput']:>8.1f}"
            f"{r['cost']:>9.4f}₽"
        )


if __name__ == "__main__":
    main()
