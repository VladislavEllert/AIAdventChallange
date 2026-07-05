# Day 21 — RAG: Document Indexing

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/scripts/rag/fetch_corpus.py`](../../agent-web/scripts/rag/fetch_corpus.py) | Downloads 24 GitLab Handbook pages → `data/rag/corpus/` |
| [`agent-web/scripts/rag/build_index.py`](../../agent-web/scripts/rag/build_index.py) | Builds 2 chunking strategies → embeddings → JSON indexes |
| [`agent-web/agent_web/services/rag/chunking.py`](../../agent-web/agent_web/services/rag/chunking.py) | Fixed-size + structural chunking strategies |
| [`agent-web/agent_web/services/rag/embedder.py`](../../agent-web/agent_web/services/rag/embedder.py) | Ollama `nomic-embed-text` client + L2 normalization |
| [`agent-web/agent_web/services/rag/index.py`](../../agent-web/agent_web/services/rag/index.py) | `Chunk` dataclass + load/save JSON index |
| [`agent-web/data/rag/chunking_compare.md`](../../agent-web/data/rag/chunking_compare.md) | Comparison of 2 chunking strategies |

## Task

Build a local RAG index from documents (≥20–30 pages): chunking → embeddings → index with metadata. Bonus: 2 chunking strategies with comparison.

## What was done

**Corpus:** 24 pages of GitLab Handbook, 93,073 words total.
- Source: `gitlab.com/gitlab-com/content-sites/handbook`
- Topics: values, code review, engineering workflow, communication, time-off, hiring, security, leadership, anti-harassment, etc.
- Each file has `<!-- source: <url> | title: <name> -->` header for citation support.

**Chunking strategies:**

| Strategy | Chunks | Avg size | Logic |
|---|---|---|---|
| Fixed (800w + 120 overlap) | 150 | 717w | Sliding window over words |
| Structural (by headings) | 479 | 199w | Split at `#`/`##`/`###`, oversized sections sub-chunked |

**Embeddings:** `nomic-embed-text` via Ollama (local, 768-dim), L2-normalized for cosine similarity.

**Index format:** JSON array of `Chunk` objects — `chunk_id`, `text`, `embedding`, `source`, `title`, `section`, `strategy`.

## Run

```bash
# 1. Fetch corpus
cd agent-web
python3 scripts/rag/fetch_corpus.py

# 2. Build indexes (requires Ollama running with nomic-embed-text)
python3 scripts/rag/build_index.py
```

Outputs:
- `data/rag/corpus/*.md` — 24 source files
- `data/rag/index_fixed.json` — 150 chunks
- `data/rag/index_structural.json` — 479 chunks
- `data/rag/chunking_compare.md` — strategy comparison

## Key insight

Structural chunking preserves semantic units (one section = one chunk, `section` field tracks heading path like `"Values > Collaboration > Kindness"`). Fixed chunking is uniform but splits across section boundaries. For retrieval, structural wins when docs have good markdown structure — GitLab Handbook qualifies.
