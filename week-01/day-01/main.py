"""AI Advent #8 — Week 1, Day 1.

Минимальный код: шлёт запрос в LLM через ProxyAPI, печатает ответ в консоль.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["PROXYAPI_KEY"],
    base_url="https://openai.api.proxyapi.ru/v1",
)

response = client.chat.completions.create(
    model="gemini-2.5-flash-lite",
    messages=[{"role": "user", "content": "Привет! Кратко: кто ты?"}],
)

print(response.choices[0].message.content)
