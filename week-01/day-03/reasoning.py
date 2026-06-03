"""День 3 — разные способы рассуждения.

Одна задача решается ОДНОЙ моделью четырьмя способами:
  A. прямой ответ (без инструкций)
  B. "решай пошагово" (chain-of-thought через system-промпт)
  C. meta: модель сама пишет промпт, потом этим промптом решает (2 вызова)
  D. группа экспертов (аналитик / инженер / критик в одном system-промпте)

Запуск:
  python reasoning.py        — гоняет все 4 способа один раз, печатает ответы.
  python reasoning.py vote   — self-consistency: каждый способ N раз при temp>0,
                               считает «ехать»/«пешком» голосованием большинства.
"""

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gemini/gemini-2.5-flash-lite"
TEMPERATURE = 0  # фиксируем → разница идёт от способа, а не от рандома

# --- параметры режима self-consistency (голосование) ---
N_VOTES = 5  # сколько раз гонять каждый способ
VOTE_TEMPERATURE = 0.7  # рандом нужен >0, иначе все N ответов одинаковы

TASK = (
    "Мне нужно помыть свою машину. Автомойка в 50 метрах от дома. "
    "Машину можно помыть только на самой автомойке — дома мыть негде. "
    "Как мне лучше добраться до автомойки — доехать на машине, которую надо "
    "помыть и которая стоит у моего дома, или дойти пешком?"
)

# --- system-промпты для способов B и D ---
SYSTEM_STEP = (
    "Решай задачу строго пошагово. Сначала распиши рассуждение шаг за шагом, "
    "проверяя каждый шаг, и только в самом конце дай однозначный финальный ответ "
    "после маркера 'ИТОГ:'."
)

SYSTEM_EXPERTS = (
    "Ты ведёшь разбор задачи силами группы из трёх экспертов:\n"
    "- АНАЛИТИК: формализует задачу, выделяет суть и подводные камни.\n"
    "- ИНЖЕНЕР: предлагает конкретное решение / вывод / алгоритм.\n"
    "- КРИТИК: ищет ошибки в рассуждении инженера, проверяет граничные случаи.\n"
    "Покажи мнение каждого эксперта по очереди. Затем совместно придите к "
    "согласованному решению и дай однозначный финальный ответ после маркера 'ИТОГ:'."
)

META_INSTRUCTION = (
    "Ты — эксперт по промпт-инжинирингу. Составь ОДИН оптимальный промпт, "
    "который поможет языковой модели максимально точно и полно решить задачу ниже. "
    "Промпт должен быть самодостаточным: включи в него саму задачу и укажи, "
    "каким методом её решать. Верни ТОЛЬКО текст промпта, без решения задачи.\n\n"
    "ЗАДАЧА:\n{task}"
)

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)


def run(messages, temperature=None):
    temp = TEMPERATURE if temperature is None else temperature
    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=temp
    )
    return response.choices[0].message.content.strip()


def method_direct():
    """A — прямой ответ без инструкций."""
    return run([{"role": "user", "content": TASK}])


def method_step():
    """B — 'решай пошагово' через system-промпт."""
    return run(
        [
            {"role": "system", "content": SYSTEM_STEP},
            {"role": "user", "content": TASK},
        ]
    )


def method_meta():
    """C — модель сама пишет промпт, затем им решает (2 вызова)."""
    generated_prompt = run(
        [{"role": "user", "content": META_INSTRUCTION.format(task=TASK)}]
    )
    print(f"\n[сгенерированный промпт]\n{generated_prompt}\n{'-' * 60}")
    return run([{"role": "user", "content": generated_prompt}])


def method_experts():
    """D — группа экспертов (аналитик / инженер / критик) в system-промпте."""
    return run(
        [
            {"role": "system", "content": SYSTEM_EXPERTS},
            {"role": "user", "content": TASK},
        ]
    )


METHODS = [
    ("A. Прямой ответ (без инструкций)", method_direct),
    ("B. Пошагово (chain-of-thought)", method_step),
    ("C. Meta (модель пишет промпт, потом решает)", method_meta),
    ("D. Группа экспертов (аналитик/инженер/критик)", method_experts),
]


CLASSIFY_SYSTEM = (
    "Прочитай ответ ниже и верни РОВНО ОДНО слово — итоговый вывод автора:\n"
    "'ехать' — если итог: добраться до автомойки на машине;\n"
    "'пешком' — если итог: дойти пешком;\n"
    "'неясно' — если однозначного вывода нет.\n"
    "Только одно слово, без знаков препинания."
)


def classify(answer):
    """Дешёвый вызов при temp=0: вытащить вердикт одним словом."""
    verdict = run(
        [
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": answer},
        ],
        temperature=0,
    )
    return verdict.strip().lower().strip(".")


def self_consistency():
    """Режим голосования: каждый способ N раз при temp>0, считаем вердикты."""
    global TEMPERATURE
    TEMPERATURE = VOTE_TEMPERATURE  # методы читают глобал → гоняют с рандомом

    print(f"Модель: {MODEL} | self-consistency | temperature={VOTE_TEMPERATURE}")
    print(f"{N_VOTES} прогонов на способ, вердикт — большинством голосов.")
    print(f"\nЗадача:\n{TASK}")
    print("\nПравильный ответ: ехать\n")

    for title, fn in METHODS:
        verdicts = [classify(fn()) for _ in range(N_VOTES)]
        tally = Counter(verdicts)
        winner = tally.most_common(1)[0][0]
        print(f"{title}\n  голоса: {dict(tally)}  →  ИТОГ: {winner}\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "vote":
        self_consistency()
        return

    print(f"Модель: {MODEL} | temperature={TEMPERATURE}")
    print(f"\nЗадача:\n{TASK}")

    for title, fn in METHODS:
        print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
        print(fn())


if __name__ == "__main__":
    main()
