from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "rag"
CORPUS_DIR = DATA_DIR / "corpus"
INDEX_FIXED = DATA_DIR / "index_fixed.json"
INDEX_STRUCTURAL = DATA_DIR / "index_structural.json"

TOP_K_RAW = 20
TOP_K_FINAL = 5
THRESHOLD = 0.5
THRESHOLD_ANSWER = 0.55

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
