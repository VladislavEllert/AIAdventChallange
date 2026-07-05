"""Build RAG index: corpus → chunks (2 strategies) → embeddings → JSON indexes + comparison."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_web.services.rag.chunking import chunk_fixed, chunk_structural
from agent_web.services.rag.embedder import embed
from agent_web.services.rag.index import Chunk, save_index
from agent_web.services.rag.config import CORPUS_DIR, INDEX_FIXED, INDEX_STRUCTURAL


def parse_header(text: str) -> tuple[str, str]:
    """Extract source URL and title from <!-- source: url | title: name --> header."""
    m = re.match(r"<!--\s*source:\s*(\S+)\s*\|\s*title:\s*(.+?)\s*-->", text)
    if m:
        return m.group(1), m.group(2)
    return "", "Unknown"


def _count_split_sentences(chunks: list[dict]) -> int:
    """Heuristic: count chunks that end without sentence-ending punctuation."""
    count = 0
    for c in chunks:
        t = c["text"].rstrip()
        if t and t[-1] not in ".!?":
            count += 1
    return count


def build_chunks(strategy: str) -> list[dict]:
    all_chunks = []
    files = sorted(CORPUS_DIR.glob("*.md"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        source, title = parse_header(text)
        body = re.sub(r"<!--.+?-->", "", text, flags=re.DOTALL).strip()
        if strategy == "fixed":
            chunks = chunk_fixed(body, source=source, title=title)
        else:
            chunks = chunk_structural(body, source=source, title=title)
        stem = f.stem
        for c in chunks:
            c["chunk_id"] = f"{stem}:{strategy}:{c['idx']}"
        all_chunks.extend(chunks)
    return all_chunks


def embed_chunks(raw_chunks: list[dict]) -> list[Chunk]:
    result = []
    total = len(raw_chunks)
    for i, c in enumerate(raw_chunks):
        print(f"\r  embedding {i+1}/{total}...", end="", flush=True)
        vec = embed(c["text"])
        result.append(Chunk(
            chunk_id=c["chunk_id"],
            text=c["text"],
            embedding=vec,
            source=c["source"],
            title=c["title"],
            section=c["section"],
            strategy=c["strategy"],
        ))
    print()
    return result


def stats(chunks: list[dict]) -> dict:
    sizes = [len(c["text"].split()) for c in chunks]
    return {
        "count": len(chunks),
        "avg": int(sum(sizes) / len(sizes)) if sizes else 0,
        "min": min(sizes) if sizes else 0,
        "max": max(sizes) if sizes else 0,
        "split_sentences": _count_split_sentences(chunks),
    }


def main():
    files = list(CORPUS_DIR.glob("*.md"))
    if not files:
        print("ERROR: corpus is empty. Run fetch_corpus.py first.")
        return 1

    total_words = sum(len(f.read_text(encoding="utf-8").split()) for f in files)
    print(f"Corpus: {len(files)} files, {total_words:,} words\n")

    print("=== Strategy: fixed ===")
    fixed_raw = build_chunks("fixed")
    fs = stats(fixed_raw)
    print(f"  chunks={fs['count']}  avg={fs['avg']}w  min={fs['min']}w  max={fs['max']}w  split_sentences≈{fs['split_sentences']}")
    print("  Embedding...")
    fixed_chunks = embed_chunks(fixed_raw)
    save_index(fixed_chunks, INDEX_FIXED)
    print(f"  Saved → {INDEX_FIXED}")

    print("\n=== Strategy: structural ===")
    struct_raw = build_chunks("structural")
    ss = stats(struct_raw)
    print(f"  chunks={ss['count']}  avg={ss['avg']}w  min={ss['min']}w  max={ss['max']}w  split_sentences≈{ss['split_sentences']}")
    print("  Embedding...")
    struct_chunks = embed_chunks(struct_raw)
    save_index(struct_chunks, INDEX_STRUCTURAL)
    print(f"  Saved → {INDEX_STRUCTURAL}")

    # Write comparison
    compare_path = INDEX_FIXED.parent / "chunking_compare.md"
    example_title = fixed_raw[0]["title"] if fixed_raw else ""
    fixed_ex = next((c for c in fixed_raw if c["title"] == example_title), None)
    struct_ex = next((c for c in struct_raw if c["title"] == example_title), None)

    compare = f"""# Chunking Strategy Comparison

## Stats

| Metric | Fixed (800w + 120 overlap) | Structural (by headings) |
|---|---|---|
| Total chunks | {fs['count']} | {ss['count']} |
| Avg size (words) | {fs['avg']} | {ss['avg']} |
| Min size (words) | {fs['min']} | {ss['min']} |
| Max size (words) | {fs['max']} | {ss['max']} |
| Split sentences (est.) | {fs['split_sentences']} | {ss['split_sentences']} |

## Analysis

**Fixed chunking** produces uniform chunk sizes (good for embedding models trained on fixed-length inputs), but splits mid-section — a heading at chunk boundary loses context.

**Structural chunking** preserves semantic units (one section = one chunk). Sections vary wildly in size — very short (stub sections) or very long (must be sub-chunked). Fewer split sentences.

**Winner for retrieval:** structural — section boundaries are natural semantic units. Fixed is a reliable fallback when markdown structure is absent.

## Example: "{example_title}"

### Fixed (first chunk)
```
{fixed_ex['text'][:400] if fixed_ex else 'N/A'}...
```
section: `{fixed_ex['section'] if fixed_ex else ''}`

### Structural (first chunk)
```
{struct_ex['text'][:400] if struct_ex else 'N/A'}...
```
section: `{struct_ex['section'] if struct_ex else ''}`
"""
    compare_path.write_text(compare, encoding="utf-8")
    print(f"\nComparison → {compare_path}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
