import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    text: str
    embedding: list
    source: str
    title: str
    section: str
    strategy: str


def save_index(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in chunks], f, ensure_ascii=False)


def load_index(path: Path, dim: int | None = None) -> list[Chunk]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chunks = [Chunk(**d) for d in data]
    if dim is not None and chunks:
        actual = len(chunks[0].embedding)
        if actual != dim:
            raise ValueError(
                f"Index {path} has {actual}d vectors, but KNOWLEDGE_BASES expects {dim}d "
                "(embed backend/index mismatch — a query embedded with the wrong backend "
                "would silently score garbage against this index)."
            )
    return chunks
