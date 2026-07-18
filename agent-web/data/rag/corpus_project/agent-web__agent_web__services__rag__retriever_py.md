<!-- source: agent-web/agent_web/services/rag/retriever.py | title: retriever.py -->

from .index import Chunk
from .embedder import embed
from .config import TOP_K_RAW, TOP_K_FINAL, THRESHOLD


def search(
    query: str,
    index: list[Chunk],
    top_k: int = TOP_K_FINAL,
    threshold: float = THRESHOLD,
    top_k_raw: int = TOP_K_RAW,
    backend: str = "ollama",
) -> tuple[list[tuple[Chunk, float]], dict]:
    q_vec = embed(query, backend=backend)
    scores = [
        (_dot(q_vec, c.embedding), c) for c in index
    ]
    scores.sort(key=lambda x: x[0], reverse=True)

    raw = scores[:top_k_raw]
    filtered = [(c, s) for s, c in raw if s >= threshold]
    result = filtered[:top_k]

    meta = {
        "top_k_raw": len(raw),
        "top_k_kept": len(filtered),
        "top_k_final": len(result),
        "best_score": raw[0][0] if raw else 0.0,
    }
    return result, meta


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
