from agent_cli.llm.dispatch import DispatchProvider
from agent_cli.llm.provider import LLMProvider
from agent_cli.core.sessions import SessionStore
from agent_cli.config import SESSIONS_DB
from agent_web.services.agent_manager import AgentManager
from agent_web.services.rag.index import Chunk, load_index
from agent_web.services.rag.config import INDEX_FIXED

_provider: LLMProvider | None = None
_session_store: SessionStore | None = None
_manager: AgentManager | None = None
_rag_index: list[Chunk] | None = None


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


def get_rag_index() -> list[Chunk]:
    global _rag_index
    if _rag_index is None:
        _rag_index = load_index(INDEX_FIXED)
    return _rag_index
