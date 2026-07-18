<!-- source: agent-web/agent_web/services/rag/config.py | title: config.py -->

import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "rag"
CORPUS_DIR = DATA_DIR / "corpus"
CORPUS_PROJECT_DIR = DATA_DIR / "corpus_project"
INDEX_FIXED = DATA_DIR / "index_fixed.json"
INDEX_STRUCTURAL = DATA_DIR / "index_structural.json"
INDEX_PROJECT_OLLAMA = DATA_DIR / "index_project.json"
INDEX_PROJECT_PROXY = DATA_DIR / "index_project_proxy.json"

TOP_K_RAW = 20
TOP_K_FINAL = 5
THRESHOLD = 0.5
THRESHOLD_ANSWER = 0.55  # calibrated days 22-24 — handbook (English) only, do not reuse elsewhere

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# Day 31: which embed backend serves the "project" KB at query time.
# Default proxyapi — this repo's Ollama box (week 6, LAN-only) isn't always
# reachable from wherever agent-web runs (this dev machine, CI). Set
# RAG_PROJECT_BACKEND=ollama to switch when that box is up and index_project.json
# has been built for it.
_PROJECT_BACKEND = os.getenv("RAG_PROJECT_BACKEND", "proxyapi")
_PROJECT_INDEX = INDEX_PROJECT_OLLAMA if _PROJECT_BACKEND == "ollama" else INDEX_PROJECT_PROXY
_PROJECT_DIM = 768 if _PROJECT_BACKEND == "ollama" else 512

# Day 31: registry of RAG knowledge bases. Each entry is self-contained — index
# file, embed backend + expected vector dim (load_index fails loudly on
# mismatch), whether the day-23 English query-rewrite applies, and the
# "don't know" gate threshold (calibrated per corpus, NOT shared — see 31.15).
KNOWLEDGE_BASES: dict[str, dict] = {
    "handbook": {
        "index_path": INDEX_FIXED,
        "label": "GitLab Handbook",
        "rewrite_to_english": True,
        "threshold_answer": THRESHOLD_ANSWER,
        "backend": "ollama",
        "dim": 768,
    },
    "project": {
        "index_path": _PROJECT_INDEX,
        "label": "Project Knowledge Base",
        "rewrite_to_english": False,  # corpus is Russian + code — EN rewrite would hurt retrieval
        # Calibrated 31.15: 10 check questions on the real proxyapi/512d index —
        # in-corpus questions scored 0.35-0.63, out-of-corpus (nonsense/unrelated)
        # scored 0.22-0.31. 0.33 sits in the gap.
        "threshold_answer": 0.33,
        "backend": _PROJECT_BACKEND,
        "dim": _PROJECT_DIM,
    },
}
