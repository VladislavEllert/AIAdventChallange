import os
from pathlib import Path
from dotenv import load_dotenv

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
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "openai/gpt-4o-mini":      {"input": 0.015,  "output": 0.06},
    "openai/gpt-4o":           {"input": 0.25,   "output": 1.00},
    "openai/gpt-4.1":          {"input": 0.20,   "output": 0.80},
    "openai/gpt-4.1-mini":     {"input": 0.02,   "output": 0.08},
    "openai/o3-mini":          {"input": 0.50,   "output": 2.00},
    "gemini/gemini-2.5-flash-lite": {"input": 0.005, "output": 0.02},
    "gemini/gemini-2.5-flash": {"input": 0.015,  "output": 0.06},
}
_DEFAULT_PRICING: dict[str, float] = {"input": 0.05, "output": 0.15}


def get_pricing(model: str) -> dict[str, float]:
    return _MODEL_PRICING.get(model, _DEFAULT_PRICING)


def calc_cost_rub(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    p = get_pricing(model)
    return (prompt_tokens / 1000) * p["input"] + (completion_tokens / 1000) * p["output"]
