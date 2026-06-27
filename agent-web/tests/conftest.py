import pytest
from fastapi.testclient import TestClient
from typing import Iterator

from agent_web.app import create_app
from agent_web.dependencies import get_session_store, get_manager
from agent_web.services.agent_manager import AgentManager
from agent_cli.llm.provider import LLMProvider, TokenUsage
from agent_cli.core.sessions import SessionStore
from agent_cli.config import DEFAULT_MODEL


class MockProvider(LLMProvider):
    """Minimal mock that returns canned responses without hitting the API."""

    def __init__(self, response: str = "Mock response"):
        self.response = response

    def chat(self, messages, model=DEFAULT_MODEL, **kwargs) -> str:
        return self.response

    def chat_stream(self, messages, model=DEFAULT_MODEL, **kwargs) -> Iterator[str]:
        for word in self.response.split():
            yield word + " "

    def chat_with_stats(self, messages, model=DEFAULT_MODEL, **kwargs):
        usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            elapsed_ms=100,
            cost_rub=0.001,
        )
        return self.response, usage


class _Ref:
    def __init__(self):
        self.usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            elapsed_ms=100,
            cost_rub=0.001,
        )


MockProvider.chat_stream_with_stats = lambda self, messages, model=DEFAULT_MODEL, **kwargs: (
    (w + " " for w in self.response.split()),
    _Ref(),
)


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def client(mock_provider, tmp_path):
    """FastAPI TestClient with mocked LLM and temp DB."""
    db_path = str(tmp_path / "test_sessions.db")
    test_store = SessionStore(db_path)
    test_manager = AgentManager(mock_provider, test_store)

    app = create_app()
    app.dependency_overrides[get_session_store] = lambda: test_store
    app.dependency_overrides[get_manager] = lambda: test_manager

    yield TestClient(app)

    app.dependency_overrides.clear()
