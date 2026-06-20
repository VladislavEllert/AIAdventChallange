"""Smoke + unit tests. No real LLM calls — everything mocked."""
import pytest
from unittest.mock import MagicMock


# ── imports ────────────────────────────────────────────────────────────────────

def test_imports_config():
    from agent_cli.config import DEFAULT_MODEL, BASE_URL, PROXYAPI_KEY
    assert DEFAULT_MODEL == "openai/gpt-4o-mini"
    assert "proxyapi" in BASE_URL


def test_imports_all():
    from agent_cli.llm.provider import LLMProvider
    from agent_cli.core.memory import Memory
    from agent_cli.core.prompt_builder import build_system_prompt
    from agent_cli.core.agent import Agent
    from agent_cli.profile.profile import UserProfile
    from agent_cli.state.machine import Stage, TRANSITIONS, can_transition
    from agent_cli.state.coordinator import TaskState
    from agent_cli.invariants.store import load_invariants, add_invariant, save_invariants
    from agent_cli.invariants.checker import check_code, check_llm


# ── memory ─────────────────────────────────────────────────────────────────────

def test_memory_add_and_get():
    from agent_cli.core.memory import Memory
    m = Memory()
    m.add_message("user", "hello")
    m.add_message("assistant", "hi")
    msgs = m.get_messages()
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "hello"}
    assert msgs[1] == {"role": "assistant", "content": "hi"}


def test_memory_overflow():
    from agent_cli.core.memory import Memory, MAX_SHORT_TERM, SUMMARIZE_AT
    m = Memory()
    for i in range(MAX_SHORT_TERM + 5):
        m.add_message("user", f"msg {i}")
    # Memory doesn't auto-trim; Agent._try_summarize() does via take_old_for_summary()
    # needs_summary() should be True once we hit SUMMARIZE_AT
    assert m.needs_summary()
    assert len(m.get_messages()) == MAX_SHORT_TERM + 5


def test_memory_pop_last_exchange():
    from agent_cli.core.memory import Memory
    m = Memory()
    m.add_message("user", "q")
    m.add_message("assistant", "a")
    m.pop_last_exchange()
    assert m.get_messages() == []


def test_memory_clear():
    from agent_cli.core.memory import Memory
    m = Memory()
    m.add_message("user", "x")
    m.summary = "sum"
    m.clear()
    assert m.get_messages() == []
    assert m.summary == ""


# ── prompt_builder ─────────────────────────────────────────────────────────────

def test_prompt_builder_basic():
    from agent_cli.core.prompt_builder import build_system_prompt
    result = build_system_prompt(persona="You are helpful.")
    assert "You are helpful." in result


def test_prompt_builder_with_invariants():
    from agent_cli.core.prompt_builder import build_system_prompt
    result = build_system_prompt(
        persona="Assistant.",
        invariants=["No RxJava", "Only Kotlin"],
    )
    assert "[ИНВАРИАНТЫ]" in result
    assert "No RxJava" in result
    assert "Only Kotlin" in result


def test_prompt_builder_with_profile():
    from agent_cli.core.prompt_builder import build_system_prompt
    result = build_system_prompt(persona="Bot.", profile_content="## Стиль\nКратко")
    assert "Профиль пользователя" in result
    assert "Кратко" in result


# ── state machine ──────────────────────────────────────────────────────────────

def test_stage_transitions_valid():
    from agent_cli.state.machine import Stage, can_transition
    assert can_transition(Stage.PLANNING, Stage.EXECUTION)
    assert can_transition(Stage.EXECUTION, Stage.VALIDATION)
    assert can_transition(Stage.VALIDATION, Stage.DONE)
    assert can_transition(Stage.VALIDATION, Stage.EXECUTION)  # retry path


def test_stage_transitions_invalid():
    from agent_cli.state.machine import Stage, can_transition
    assert not can_transition(Stage.PLANNING, Stage.DONE)
    assert not can_transition(Stage.PLANNING, Stage.VALIDATION)
    assert not can_transition(Stage.DONE, Stage.PLANNING)
    assert not can_transition(Stage.EXECUTION, Stage.PLANNING)


# ── profile ────────────────────────────────────────────────────────────────────

def test_profile_roundtrip(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile

    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        p = UserProfile(
            name="test",
            persona="Developer",
            style="Brief",
            rules="No RxJava",
            stack="Kotlin",
            interests="Mobile",
        )
        p.save()
        loaded = UserProfile.load("test")
        assert loaded.persona == "Developer"
        assert loaded.style == "Brief"
        assert loaded.rules == "No RxJava"
        assert loaded.stack == "Kotlin"
        assert loaded.interests == "Mobile"
    finally:
        cfg.PROFILES_DIR = orig


def test_profile_to_prompt_text():
    from agent_cli.profile.profile import UserProfile
    p = UserProfile(name="x", style="Brief", stack="Python")
    text = p.to_prompt_text()
    assert "Стиль" in text
    assert "Brief" in text
    assert "Стек" in text
    assert "Python" in text


def test_profile_list_all(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile

    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        UserProfile(name="alpha").save()
        UserProfile(name="beta").save()
        profiles = UserProfile.list_all()
        assert "alpha" in profiles
        assert "beta" in profiles
    finally:
        cfg.PROFILES_DIR = orig


# ── task state persist ─────────────────────────────────────────────────────────

def test_task_state_persist(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.state.coordinator import TaskState
    from agent_cli.state.machine import Stage

    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        ts = TaskState("abc123", "Do something")
        ts.plan = "Step 1: ..."
        ts.stage = Stage.EXECUTION
        ts.save()

        loaded = TaskState.load("abc123")
        assert loaded.task_id == "abc123"
        assert loaded.stage == Stage.EXECUTION
        assert loaded.plan == "Step 1: ..."
        assert loaded.request == "Do something"
    finally:
        cfg.TASKS_DIR = orig


def test_task_state_latest(tmp_path):
    import time
    import agent_cli.config as cfg
    from agent_cli.state.coordinator import TaskState

    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        t1 = TaskState("first", "task 1")
        t1.save()
        time.sleep(0.01)
        t2 = TaskState("second", "task 2")
        t2.save()

        latest = TaskState.latest()
        assert latest is not None
        assert latest.task_id == "second"
    finally:
        cfg.TASKS_DIR = orig


# ── invariants ─────────────────────────────────────────────────────────────────

def test_invariants_roundtrip(tmp_path):
    import agent_cli.config as cfg
    import agent_cli.invariants.store as store

    orig = cfg.INVARIANTS_DIR
    cfg.INVARIANTS_DIR = str(tmp_path)
    try:
        store.add_invariant("No RxJava")
        store.add_invariant("Only Kotlin")
        invs = store.load_invariants()
        assert "No RxJava" in invs
        assert "Only Kotlin" in invs
    finally:
        cfg.INVARIANTS_DIR = orig


def test_invariants_no_duplicates(tmp_path):
    import agent_cli.config as cfg
    import agent_cli.invariants.store as store

    orig = cfg.INVARIANTS_DIR
    cfg.INVARIANTS_DIR = str(tmp_path)
    try:
        store.add_invariant("Rule A")
        store.add_invariant("Rule A")  # duplicate
        invs = store.load_invariants()
        assert invs.count("Rule A") == 1
    finally:
        cfg.INVARIANTS_DIR = orig


def test_check_code_no_violation():
    from agent_cli.invariants.checker import check_code
    ok, _ = check_code("Use Kotlin coroutines for async.", ["Запрет RxJava"])
    assert ok


# ── agent mock ─────────────────────────────────────────────────────────────────

def test_agent_respond_mock():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "Ответ агента"
    agent = Agent(provider=mock, model="test-model")

    response = agent.respond("Привет")
    assert response == "Ответ агента"
    assert len(agent.memory.short_term) == 2
    mock.chat.assert_called_once()


def test_agent_memory_not_polluted_on_invariant_pop():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "bad response"
    agent = Agent(provider=mock)

    agent.respond("question")
    assert len(agent.memory.short_term) == 2
    agent.memory.pop_last_exchange()
    assert len(agent.memory.short_term) == 0


# ── coordinator mock ───────────────────────────────────────────────────────────

def test_coordinator_full_run_mock():
    """Happy path: planning→execution→validation OK→done."""
    from agent_cli.llm.provider import LLMProvider
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    from agent_cli.state.machine import Stage, VALIDATION_OK_MARKER

    responses = [
        "Шаг 1: сделать X. <<ПЛАН ГОТОВ>>",
        "Выполнено: X сделано. <<ВЫПОЛНЕНО>>",
        f"Всё соответствует плану. {VALIDATION_OK_MARKER}",
    ]
    call_count = 0

    def fake_chat(messages, model, **kwargs):
        nonlocal call_count
        r = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return r

    mock = MagicMock(spec=LLMProvider)
    mock.chat.side_effect = fake_chat

    task = TaskState("t001", "Сделай X")
    coord = TaskCoordinator(provider=mock, interactive=False)

    import agent_cli.config as cfg
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        orig = cfg.TASKS_DIR
        cfg.TASKS_DIR = tmp
        try:
            result = coord.run(task, output_fn=lambda _: None)
        finally:
            cfg.TASKS_DIR = orig

    assert result.stage == Stage.DONE
    assert result.plan != ""
    assert result.execution_result != ""
