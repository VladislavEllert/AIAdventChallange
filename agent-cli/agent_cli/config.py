import os
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Two-pass load, both non-overriding (first value found for a given key wins):
# 1) usecwd=True — search from the process's cwd upward. This is where a
#    running app's own .env lives (e.g. agent-web/.env has OLLAMA_CHAT_URL,
#    COMFYUI_URL — keys that only make sense per-app).
# 2) bare load_dotenv() — frame-based search from this file's location, i.e.
#    agent-cli/.env. Fills in repo-wide keys (PROXYAPI_KEY) that pass 1 may
#    have missed because the running app's own .env doesn't define them.
load_dotenv(find_dotenv(usecwd=True))
load_dotenv()

PROXYAPI_KEY: str = os.getenv("PROXYAPI_KEY", "")
BASE_URL: str = "https://openai.api.proxyapi.ru/v1"
DEFAULT_MODEL: str = "openai/gpt-4o-mini"

OLLAMA_CHAT_URL: str = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/v1")
COMFYUI_URL: str = os.getenv("COMFYUI_URL", "http://localhost:8188")

_ROOT = Path(__file__).parent.parent
DATA_DIR = str(_ROOT / "data")
PROFILES_DIR = str(_ROOT / "data" / "profiles")
TASKS_DIR = str(_ROOT / "data" / "tasks")
INVARIANTS_DIR = str(_ROOT / "data" / "invariants")
SESSIONS_DB = str(_ROOT / "data" / "sessions.db")

# Pricing per 1K tokens in rubles (ProxyAPI, approximate — verify at proxyapi.ru/prices)
# "type": text models stream tokens like any LLMProvider; image models go through
# a separate non-token path (ComfyUI) — see agent_web/services/comfyui_client.py.
_MODEL_PRICING: dict[str, dict] = {
    "openai/gpt-4o-mini":      {"input": 0.015,  "output": 0.06, "type": "text"},
    "openai/gpt-4o":           {"input": 0.25,   "output": 1.00, "type": "text"},
    "openai/gpt-4.1":          {"input": 0.20,   "output": 0.80, "type": "text"},
    "openai/gpt-4.1-mini":     {"input": 0.02,   "output": 0.08, "type": "text"},
    "openai/o3-mini":          {"input": 0.50,   "output": 2.00, "type": "text"},
    "gemini/gemini-2.5-flash-lite": {"input": 0.005, "output": 0.02, "type": "text"},
    "gemini/gemini-2.5-flash": {"input": 0.015,  "output": 0.06, "type": "text"},
    "ollama/qwen3:4b":         {"input": 0.0,    "output": 0.0,  "type": "text"},
    "comfyui/sdxl":            {"input": 0.0,    "output": 0.0,  "type": "image"},
}
_DEFAULT_PRICING: dict[str, float] = {"input": 0.05, "output": 0.15}


def get_pricing(model: str) -> dict[str, float]:
    return _MODEL_PRICING.get(model, _DEFAULT_PRICING)


def get_model_type(model: str) -> str:
    return _MODEL_PRICING.get(model, {}).get("type", "text")


def calc_cost_rub(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    p = get_pricing(model)
    return (prompt_tokens / 1000) * p["input"] + (completion_tokens / 1000) * p["output"]
