"""
Day 26 — smoke test for local LLM (Ollama qwen3:4b on Windows LAN server).

Runs 3 requests of increasing complexity against the Ollama OpenAI-compatible
endpoint and prints latency + response for each. No mocking — real HTTP calls.

Usage:
    python week-06/day-26/local_llm_smoke.py
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Explicit path: repo root .env (Telegram bot) would otherwise shadow
# agent-web/.env when this script runs from repo root, silently dropping
# OLLAMA_CHAT_URL back to localhost.
load_dotenv(Path(__file__).resolve().parents[2] / "agent-web" / ".env")

OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://192.168.0.33:11434/v1")
MODEL = "qwen3:4b"

PROMPTS = [
    ("simple fact", "Столица Франции — какой город? Ответь одним словом."),
    ("reasoning", "У Маши было 5 яблок, она отдала 2 Пете и купила ещё 4. Сколько яблок у Маши? Объясни ход мысли кратко."),
    ("code", "Напиши функцию на Python, которая проверяет, является ли строка палиндромом (без учёта регистра и пробелов)."),
]


def main() -> int:
    print(f"Ollama endpoint: {OLLAMA_CHAT_URL}")
    print(f"Model: {MODEL}\n")

    client = OpenAI(api_key="ollama", base_url=OLLAMA_CHAT_URL)

    ok = 0
    for label, prompt in PROMPTS:
        print(f"--- [{label}] ---")
        print(f"> {prompt}")
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            elapsed_ms = (time.time() - t0) * 1000
            text = resp.choices[0].message.content or ""
            print(f"< {text.strip()}")
            print(f"  ({elapsed_ms:.0f}ms, {resp.usage.total_tokens if resp.usage else '?'} tok)\n")
            ok += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")

    print(f"{ok}/{len(PROMPTS)} requests succeeded.")
    return 0 if ok == len(PROMPTS) else 1


if __name__ == "__main__":
    sys.exit(main())
