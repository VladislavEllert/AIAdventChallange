<!-- source: agent-web/agent_web/services/settings_store.py | title: settings_store.py -->

"""Persistent settings store (JSON file)."""
import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SETTINGS_PATH = _DATA_DIR / "settings.json"

_DEFAULTS: dict = {
    "short_term_limit": 16,
    "keep_recent": 8,
    "default_model": "openai/gpt-4o-mini",
    "auto_profile_update": False,
    "theme": "system",
    # Day 29: text generation params (applied to every chat call, both providers)
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 1.0,
    "num_ctx": 4096,  # Ollama-only (extra_body); ignored by ProxyAPI models
    # Day 29: image generation params (SDXL/ComfyUI only)
    "image_steps": 20,
    "image_cfg": 8.0,
    "image_seed": None,  # None = random each generation
    "image_width": 1024,
    "image_height": 1024,
}


def load_settings() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        return {**_DEFAULTS, **data}
    except Exception:
        return dict(_DEFAULTS)


def save_settings(patch: dict) -> dict:
    current = load_settings()
    merged = {**current, **patch}
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _apply_memory_settings(merged)
    return merged


def _apply_memory_settings(settings: dict) -> None:
    """Monkey-patch agent_cli memory constants so new agents use updated N."""
    try:
        import agent_cli.core.memory as mem
        mem.SUMMARIZE_AT = int(settings.get("short_term_limit", 16))
        mem.KEEP_RECENT = int(settings.get("keep_recent", 8))
    except Exception:
        pass


# Apply on import so settings survive server restart
_apply_memory_settings(load_settings())
