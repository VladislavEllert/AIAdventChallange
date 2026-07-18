from agent_cli.llm.dispatch import DispatchProvider
from agent_cli.llm.provider import LLMProvider
from agent_cli.core.sessions import SessionStore
from agent_cli.config import SESSIONS_DB
from agent_web.services.agent_manager import AgentManager
from agent_web.services.rag.index import Chunk, load_index
from agent_web.services.rag.config import KNOWLEDGE_BASES

_provider: LLMProvider | None = None
_session_store: SessionStore | None = None
_manager: AgentManager | None = None
_rag_indexes: dict[str, list[Chunk]] = {}


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = DispatchProvider()
    return _provider


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore(SESSIONS_DB)
    return _session_store


def get_manager() -> AgentManager:
    global _manager
    if _manager is None:
        _manager = AgentManager(get_provider(), get_session_store())
    return _manager


def get_rag_index(kb: str = "handbook") -> list[Chunk]:
    """Day 31: multi-KB cache, one entry per knowledge base (handbook/project)."""
    if kb not in KNOWLEDGE_BASES:
        raise ValueError(f"Unknown knowledge base: {kb!r} (known: {list(KNOWLEDGE_BASES)})")
    if kb not in _rag_indexes:
        cfg = KNOWLEDGE_BASES[kb]
        _rag_indexes[kb] = load_index(cfg["index_path"], dim=cfg["dim"])
    return _rag_indexes[kb]
