"""
Day 26 — live smoke test against Ollama LAN server (192.168.0.33).

Skips automatically if the server is unreachable (e.g. Mac is on VPN that
blocks LAN routing, or the Windows box is off). Run with the box up and
VPN off to get real coverage.
"""
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from openai import OpenAI

# agent_cli.config reads OLLAMA_CHAT_URL once at import time, and by the time
# this test runs it may already be imported (e.g. via conftest) with the
# wrong .env resolved (repo root .env shadows agent-web/.env by cwd search).
# override=True + reading os.environ directly (not the cached config
# constant) sidesteps that import-order trap.
load_dotenv(Path(__file__).resolve().parents[2] / "agent-web" / ".env", override=True)

OLLAMA_CHAT_URL = os.environ.get("OLLAMA_CHAT_URL", "http://localhost:11434/v1")

MODEL = "qwen3:4b"


def _ollama_reachable() -> bool:
    host = urlparse(OLLAMA_CHAT_URL).hostname
    port = urlparse(OLLAMA_CHAT_URL).port or 11434
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_reachable(),
    reason=f"Ollama not reachable at {OLLAMA_CHAT_URL} (server off, or Mac VPN blocking LAN)",
)


def test_ollama_returns_nonempty_response():
    client = OpenAI(api_key="ollama", base_url=OLLAMA_CHAT_URL)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say 'ok' and nothing else."}],
    )
    text = resp.choices[0].message.content or ""
    assert text.strip() != ""


def test_ollama_tags_lists_qwen3():
    import httpx

    base = OLLAMA_CHAT_URL.rsplit("/v1", 1)[0]
    resp = httpx.get(f"{base}/api/tags", timeout=5)
    resp.raise_for_status()
    names = [m["name"] for m in resp.json().get("models", [])]
    assert any("qwen3" in n for n in names)


def test_dispatch_provider_routes_ollama_model_live():
    """Day 27: DispatchProvider('ollama/qwen3:4b') must reach the real box,
    not just the raw OpenAI client used above."""
    from unittest.mock import MagicMock
    from agent_cli.llm.dispatch import DispatchProvider
    from agent_cli.llm.ollama import OllamaProvider

    # Force OllamaProvider to read the freshly-loaded OLLAMA_CHAT_URL rather
    # than whatever agent_cli.config cached at its own import time.
    ollama = OllamaProvider.__new__(OllamaProvider)
    ollama.client = OpenAI(api_key="ollama", base_url=OLLAMA_CHAT_URL)

    d = DispatchProvider(proxyapi=MagicMock(), ollama=ollama)
    text = d.chat([{"role": "user", "content": "Say 'ok' and nothing else."}], "ollama/qwen3:4b")
    assert text.strip() != ""
