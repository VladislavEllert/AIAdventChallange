"""Embedding — two backends, selected per knowledge base (see rag/config.py).

- ollama: nomic-embed-text, 768d. Local/LAN Ollama box, no API cost.
- proxyapi: text-embedding-3-small, 512d (dimensions= truncation). Same
  PROXYAPI_KEY as chat, works from CI / anywhere without LAN access to Ollama.
"""
import json
import math
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.getenv("RAG_OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL_OLLAMA = "nomic-embed-text"
EMBED_MODEL_PROXYAPI = "text-embedding-3-small"
PROXYAPI_DIM = 512

MAX_WORDS = 600


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _embed_ollama(text: str) -> list[float]:
    # Truncate to avoid Ollama 500 on very long inputs
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])

    payload = json.dumps({"model": EMBED_MODEL_OLLAMA, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return _l2_normalize(data["embedding"])
        except urllib.error.HTTPError as e:
            if attempt == 2:
                raise
            # retry with half the text on 500
            words = text.split()
            text = " ".join(words[: len(words) // 2])
            payload = json.dumps({"model": EMBED_MODEL_OLLAMA, "prompt": text}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
    return []


def _embed_proxyapi(text: str) -> list[float]:
    from agent_cli.config import PROXYAPI_KEY, BASE_URL
    from openai import OpenAI

    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])

    client = OpenAI(api_key=PROXYAPI_KEY, base_url=BASE_URL)
    resp = client.embeddings.create(
        model=EMBED_MODEL_PROXYAPI, input=text, dimensions=PROXYAPI_DIM
    )
    return _l2_normalize(resp.data[0].embedding)


def embed(text: str, backend: str = "ollama") -> list[float]:
    if backend == "proxyapi":
        return _embed_proxyapi(text)
    if backend == "ollama":
        return _embed_ollama(text)
    raise ValueError(f"Unknown embed backend: {backend!r} (expected 'ollama' or 'proxyapi')")


def embed_batch(texts: list[str], backend: str = "ollama") -> list[list[float]]:
    return [embed(t, backend=backend) for t in texts]
