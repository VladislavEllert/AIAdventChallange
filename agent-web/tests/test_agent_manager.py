import pytest
from agent_web.services.agent_manager import AgentManager
from tests.conftest import MockProvider
from agent_cli.core.sessions import SessionStore


@pytest.fixture
def store(tmp_path):
    return SessionStore(str(tmp_path / "sessions.db"))


@pytest.fixture
def manager(store):
    return AgentManager(MockProvider(), store)


def test_creates_new_agent(manager):
    agent = manager.get_or_create("ses1")
    assert agent is not None


def test_returns_same_instance(manager):
    a1 = manager.get_or_create("ses1")
    a2 = manager.get_or_create("ses1")
    assert a1 is a2


def test_different_sessions_different_agents(manager):
    a1 = manager.get_or_create("ses1")
    a2 = manager.get_or_create("ses2")
    assert a1 is not a2


def test_save_and_reload(manager, store):
    sid = store.create_session(name="test")
    agent = manager.get_or_create(sid)
    agent.memory.add_message("user", "hello")
    agent.memory.add_message("assistant", "world")

    manager.save(sid)

    # Remove from cache and reload
    manager.remove(sid)
    reloaded = manager.get_or_create(sid)
    msgs = reloaded.memory.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["content"] == "hello"


def test_remove_clears_cache(manager):
    manager.get_or_create("ses1")
    manager.remove("ses1")
    assert "ses1" not in manager._agents


def test_persona_applied(manager):
    agent = manager.get_or_create("ses1", persona="You are a pirate")
    assert agent.persona == "You are a pirate"


def test_model_applied(manager):
    agent = manager.get_or_create("ses1", model="openai/gpt-4o")
    assert agent.model == "openai/gpt-4o"
