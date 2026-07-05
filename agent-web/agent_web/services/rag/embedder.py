import json
import math
import urllib.request
from .config import OLLAMA_URL, EMBED_MODEL


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


MAX_WORDS = 600


def embed(text: str) -> list[float]:
    # Truncate to avoid Ollama 500 on very long inputs
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])

    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
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
            payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
    return []


def embed_batch(texts: list[str]) -> list[list[float]]:
    return [embed(t) for t in texts]
