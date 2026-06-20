"""Coverage tests for all uncovered branches and modules."""
import pytest
from unittest.mock import MagicMock, patch, call
import tempfile
import os


# ── __main__ ──────────────────────────────────────────────────────────────────

def test_main_calls_tui_run():
    with patch("agent_cli.tui.TUI.run") as mock_run, \
         patch("agent_cli.llm.proxyapi.OpenAI"):
        from agent_cli.__main__ import main
        main()
        mock_run.assert_called_once()


# ── llm/provider abstract ──────────────────────────────────────────────────────

def test_llm_provider_not_instantiable():
    from agent_cli.llm.provider import LLMProvider
    with pytest.raises(TypeError):
        LLMProvider()


def test_llm_provider_subclass_works():
    from agent_cli.llm.provider import LLMProvider
    from typing import Iterator

    class ConcreteProvider(LLMProvider):
        def chat(self, messages, model, **kwargs) -> str:
            return "ok"
        def chat_stream(self, messages, model, **kwargs) -> Iterator[str]:
            yield "ok"

    p = ConcreteProvider()
    assert p.chat([], "m") == "ok"
    assert list(p.chat_stream([], "m")) == ["ok"]


# ── llm/proxyapi ──────────────────────────────────────────────────────────────

def test_proxyapi_chat():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = "Hello"

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        from agent_cli.llm.proxyapi import ProxyAPIProvider
        provider = ProxyAPIProvider()
        result = provider.chat([{"role": "user", "content": "hi"}], "gpt-4o-mini")

    assert result == "Hello"
    mock_client.chat.completions.create.assert_called_once()


def test_proxyapi_chat_stream():
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = "Hel"
    chunk2 = MagicMock()
    chunk2.choices[0].delta.content = "lo"
    chunk3 = MagicMock()
    chunk3.choices[0].delta.content = None  # skipped

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        from agent_cli.llm.proxyapi import ProxyAPIProvider
        provider = ProxyAPIProvider()
        result = list(provider.chat_stream([{"role": "user", "content": "hi"}], "gpt-4o-mini"))

    assert result == ["Hel", "lo"]


def test_proxyapi_chat_none_content():
    """None content becomes empty string."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = None

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        from agent_cli.llm.proxyapi import ProxyAPIProvider
        provider = ProxyAPIProvider()
        result = provider.chat([], "m")

    assert result == ""


# ── core/agent respond_stream ──────────────────────────────────────────────────

def test_agent_respond_stream():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat_stream.return_value = iter(["Hello", " ", "World"])
    agent = Agent(provider=mock, model="test")

    chunks = list(agent.respond_stream("hi"))
    assert chunks == ["Hello", " ", "World"]
    # Memory should have user + assembled assistant
    assert len(agent.memory.short_term) == 2
    assert agent.memory.short_term[0]["role"] == "user"
    assert agent.memory.short_term[1]["content"] == "Hello World"


def test_agent_respond_stream_with_context():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat_stream.return_value = iter(["response"])
    agent = Agent(provider=mock)

    chunks = list(agent.respond_stream("question", working_context="ctx"))
    assert chunks == ["response"]
    # working_context injected into system message
    call_args = mock.chat_stream.call_args
    system_msg = call_args[0][0][0]["content"]
    assert "ctx" in system_msg


# ── prompt_builder missing branches ───────────────────────────────────────────

def test_prompt_builder_with_summary():
    from agent_cli.core.prompt_builder import build_system_prompt
    result = build_system_prompt(persona="Bot.", summary="Old context.")
    assert "Резюме" in result
    assert "Old context." in result


def test_prompt_builder_with_working_context():
    from agent_cli.core.prompt_builder import build_system_prompt
    result = build_system_prompt(persona="Bot.", working_context="Task: make X")
    assert "Рабочий контекст" in result
    assert "Task: make X" in result


# ── invariants/checker ─────────────────────────────────────────────────────────

def test_check_code_finds_violation():
    from agent_cli.invariants.checker import check_code
    ok, msg = check_code(
        "Here is RxJava code: Observable.just(1)",
        ["Запрет rxjava в примерах"],
    )
    assert not ok
    assert msg != ""


def test_check_code_no_violation_on_short_word():
    """Words ≤3 chars skipped — no false positives."""
    from agent_cli.invariants.checker import check_code
    ok, _ = check_code("Use rx", ["Запрет rx"])
    assert ok  # "rx" is 2 chars, skipped


def test_check_llm_ok():
    from agent_cli.invariants.checker import check_llm
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "ОК"
    ok, msg = check_llm("Good response with Kotlin.", ["No RxJava"], mock, "test")
    assert ok
    assert msg == ""
    mock.chat.assert_called_once()


def test_check_llm_violation():
    from agent_cli.invariants.checker import check_llm
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "НАРУШЕНИЕ: нарушен инвариант No RxJava"
    ok, msg = check_llm("Uses RxJava.subscribe()", ["No RxJava"], mock, "test")
    assert not ok
    assert "No RxJava" in msg


def test_check_llm_violation_no_colon():
    """НАРУШЕНИЕ without colon → full text as violation."""
    from agent_cli.invariants.checker import check_llm
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "НАРУШЕНИЕ без двоеточия"
    ok, msg = check_llm("something", ["rule"], mock, "test")
    assert not ok
    assert msg != ""


def test_check_llm_empty_invariants_skips_llm():
    from agent_cli.invariants.checker import check_llm
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    ok, msg = check_llm("anything", [], mock, "test")
    assert ok
    assert msg == ""
    mock.chat.assert_not_called()


# ── profile/extractor ─────────────────────────────────────────────────────────

def test_extractor_routes_to_valid_layer():
    from agent_cli.profile.extractor import route_fact, _LAYERS
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "stack"
    result = route_fact("Я пишу на Kotlin", mock, "test")
    assert result == "stack"


def test_extractor_fallback_on_unknown():
    from agent_cli.profile.extractor import route_fact
    from agent_cli.llm.provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.chat.return_value = "unknown_garbage"
    result = route_fact("что-то непонятное", mock, "test")
    assert result == "persona"  # fallback


def test_extractor_all_valid_layers():
    from agent_cli.profile.extractor import route_fact, _LAYERS
    from agent_cli.llm.provider import LLMProvider

    for layer in _LAYERS:
        mock = MagicMock(spec=LLMProvider)
        mock.chat.return_value = layer
        result = route_fact("some fact", mock, "test")
        assert result == layer


# ── profile/profile missing branches ──────────────────────────────────────────

def test_profile_to_prompt_text_partial_fields():
    """Only non-empty fields appear in prompt text."""
    from agent_cli.profile.profile import UserProfile
    p = UserProfile(name="x", style="Brief")  # only style set
    text = p.to_prompt_text()
    assert "Brief" in text
    assert "Стиль" in text
    assert "Стек" not in text   # empty
    assert "Увлечения" not in text  # empty


def test_profile_to_prompt_text_empty():
    from agent_cli.profile.profile import UserProfile
    p = UserProfile(name="x")
    text = p.to_prompt_text()
    assert text == ""


def test_profile_to_md_contains_all_sections(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile

    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        p = UserProfile(name="full", persona="Dev", style="Short", rules="No RxJava", stack="Python", interests="OSS")
        p.save()
        content = (tmp_path / "full.md").read_text()
        assert "## Профиль" in content
        assert "## Стиль" in content
        assert "## Правила/ограничения" in content
        assert "## Стек" in content
        assert "## Увлечения" in content
    finally:
        cfg.PROFILES_DIR = orig


def test_profile_load_missing_raises():
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        orig = cfg.PROFILES_DIR
        cfg.PROFILES_DIR = tmp
        try:
            with pytest.raises(FileNotFoundError):
                UserProfile.load("nonexistent")
        finally:
            cfg.PROFILES_DIR = orig


# ── state/coordinator missing branches ────────────────────────────────────────

def _make_coord_mock_responses(responses: list[str], tmp_dir: str):
    """Helper: coordinator with mock provider returning given responses."""
    from agent_cli.llm.provider import LLMProvider
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    import agent_cli.config as cfg

    call_idx = {"i": 0}

    def fake_chat(messages, model, **kwargs):
        idx = min(call_idx["i"], len(responses) - 1)
        call_idx["i"] += 1
        return responses[idx]

    mock = MagicMock(spec=LLMProvider)
    mock.chat.side_effect = fake_chat

    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = tmp_dir
    return mock, orig


def test_coordinator_validation_retry_path():
    """Validation fails once → execution retried → validation OK."""
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    from agent_cli.state.machine import Stage, VALIDATION_OK_MARKER, VALIDATION_FAIL_MARKER
    import agent_cli.config as cfg

    responses = [
        "Шаг 1. <<ПЛАН ГОТОВ>>",             # planning
        "Выполнено. <<ВЫПОЛНЕНО>>",           # execution 1
        f"Ошибка. {VALIDATION_FAIL_MARKER}",  # validation fail
        "Исправлено. <<ВЫПОЛНЕНО>>",          # execution retry
        f"Всё ок. {VALIDATION_OK_MARKER}",   # validation ok
    ]

    with tempfile.TemporaryDirectory() as tmp:
        mock, orig = _make_coord_mock_responses(responses, tmp)
        try:
            coord = TaskCoordinator(provider=mock, interactive=False)
            task = TaskState("r001", "Задача с ретраем")
            result = coord.run(task, output_fn=lambda _: None)
        finally:
            cfg.TASKS_DIR = orig

    assert result.stage == Stage.DONE
    assert mock.chat.call_count == 5


def test_coordinator_execution_gets_validation_feedback():
    """On retry, execution agent receives validation feedback in prompt."""
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    from agent_cli.state.machine import Stage, VALIDATION_OK_MARKER, VALIDATION_FAIL_MARKER
    import agent_cli.config as cfg

    captured_prompts: list[str] = []

    def fake_chat(messages, model, **kwargs):
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        captured_prompts.append(user_msg)
        calls = len(captured_prompts)
        if calls == 1:
            return "Plan ready. <<ПЛАН ГОТОВ>>"
        if calls == 2:
            return "Execution done. <<ВЫПОЛНЕНО>>"
        if calls == 3:
            return f"Bad output. {VALIDATION_FAIL_MARKER}"
        if calls == 4:
            return "Fixed. <<ВЫПОЛНЕНО>>"
        return f"All good. {VALIDATION_OK_MARKER}"

    mock = MagicMock()
    mock.chat.side_effect = fake_chat

    with tempfile.TemporaryDirectory() as tmp:
        import agent_cli.config as cfg
        orig = cfg.TASKS_DIR
        cfg.TASKS_DIR = tmp
        try:
            coord = TaskCoordinator(provider=mock, interactive=False)
            task = TaskState("fb001", "Сделай X")
            coord.run(task, output_fn=lambda _: None)
        finally:
            cfg.TASKS_DIR = orig

    # 4th prompt is execution retry — should contain validation feedback
    retry_prompt = captured_prompts[3]
    assert "Фидбек от валидации" in retry_prompt


def test_coordinator_max_retries_stops():
    """After MAX_RETRIES failed validations, coordinator stops gracefully."""
    from agent_cli.state.coordinator import TaskCoordinator, TaskState, MAX_RETRIES
    from agent_cli.state.machine import Stage, VALIDATION_FAIL_MARKER
    import agent_cli.config as cfg

    def fake_chat(messages, model, **kwargs):
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        if "Задача" in user_msg and "План" not in user_msg and "Результат" not in user_msg:
            return "Plan. <<ПЛАН ГОТОВ>>"
        if "Результат" not in user_msg:
            return "Exec. <<ВЫПОЛНЕНО>>"
        return f"Always fails. {VALIDATION_FAIL_MARKER}"

    mock = MagicMock()
    mock.chat.side_effect = fake_chat

    with tempfile.TemporaryDirectory() as tmp:
        import agent_cli.config as cfg
        orig = cfg.TASKS_DIR
        cfg.TASKS_DIR = tmp
        try:
            coord = TaskCoordinator(provider=mock, interactive=False)
            task = TaskState("mx001", "Задача что всегда падает")
            output_lines: list[str] = []
            result = coord.run(task, output_fn=output_lines.append)
        finally:
            cfg.TASKS_DIR = orig

    assert result.stage != Stage.DONE
    assert any("лимит" in line.lower() or "попыт" in line.lower() for line in output_lines)


def test_coordinator_pause_on_user_reject():
    """User rejects confirmation → task pauses, resumable."""
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    from agent_cli.state.machine import Stage
    import agent_cli.config as cfg

    responses = ["Plan done. <<ПЛАН ГОТОВ>>"]

    mock = MagicMock()
    mock.chat.side_effect = responses

    with tempfile.TemporaryDirectory() as tmp:
        orig = cfg.TASKS_DIR
        cfg.TASKS_DIR = tmp
        try:
            coord = TaskCoordinator(provider=mock, interactive=True)
            task = TaskState("p001", "Пауза задача")
            output_lines: list[str] = []
            result = coord.run(
                task,
                output_fn=output_lines.append,
                confirm_fn=lambda _: False,  # always reject
            )
        finally:
            cfg.TASKS_DIR = orig

    assert result.stage == Stage.EXECUTION  # paused before execution
    assert any("приостановлена" in line for line in output_lines)


def test_coordinator_pause_confirm_continue():
    """User accepts confirmation → pipeline continues."""
    from agent_cli.state.coordinator import TaskCoordinator, TaskState
    from agent_cli.state.machine import Stage, VALIDATION_OK_MARKER
    import agent_cli.config as cfg

    responses = [
        "Plan. <<ПЛАН ГОТОВ>>",
        "Exec. <<ВЫПОЛНЕНО>>",
        f"OK. {VALIDATION_OK_MARKER}",
    ]
    call_idx = {"i": 0}

    def fake_chat(messages, model, **kwargs):
        r = responses[min(call_idx["i"], len(responses) - 1)]
        call_idx["i"] += 1
        return r

    mock = MagicMock()
    mock.chat.side_effect = fake_chat

    with tempfile.TemporaryDirectory() as tmp:
        import agent_cli.config as cfg
        orig = cfg.TASKS_DIR
        cfg.TASKS_DIR = tmp
        try:
            coord = TaskCoordinator(provider=mock, interactive=True)
            task = TaskState("c001", "Полный прогон с подтверждением")
            result = coord.run(
                task,
                output_fn=lambda _: None,
                confirm_fn=lambda _: True,  # always accept
            )
        finally:
            cfg.TASKS_DIR = orig

    assert result.stage == Stage.DONE


# ── tui handler unit tests ────────────────────────────────────────────────────

def _make_tui():
    """Instantiate TUI with mocked provider (no real OpenAI calls)."""
    with patch("agent_cli.llm.proxyapi.OpenAI"):
        from agent_cli.tui import TUI
        tui = TUI()
    return tui


def test_tui_show_help(capsys):
    tui = _make_tui()
    # Shouldn't raise — rich prints to terminal
    tui._show_help()


def test_tui_handle_profile_no_profile(capsys):
    tui = _make_tui()
    tui.current_profile = None
    with patch.object(tui, "_prompt", return_value=""):
        tui._handle_profile(["show"])
    # Just checking no exception raised


def test_tui_handle_profile_list(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        from agent_cli.profile.profile import UserProfile
        UserProfile(name="alpha").save()
        tui = _make_tui()
        tui._handle_profile(["list"])
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_switch_valid(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        from agent_cli.profile.profile import UserProfile
        UserProfile(name="myprofile", style="Short").save()
        tui = _make_tui()
        tui._handle_profile(["switch", "myprofile"])
        assert tui.current_profile is not None
        assert tui.current_profile.name == "myprofile"
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_switch_not_found(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui._handle_profile(["switch", "ghost"])
        assert tui.current_profile is None
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_switch_prompt(tmp_path):
    """No name arg → _prompt called."""
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        from agent_cli.profile.profile import UserProfile
        UserProfile(name="prompted").save()
        tui = _make_tui()
        with patch.object(tui, "_prompt", return_value="prompted"):
            tui._handle_profile(["switch"])
        assert tui.current_profile.name == "prompted"
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_switch_empty_prompt(tmp_path):
    """Empty prompt → no switch."""
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        with patch.object(tui, "_prompt", return_value=""):
            tui._handle_profile(["switch"])
        assert tui.current_profile is None
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_show_with_profile(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        from agent_cli.profile.profile import UserProfile
        UserProfile(name="x", style="Brief").save()
        tui = _make_tui()
        tui.current_profile = UserProfile.load("x")
        tui._handle_profile(["show"])
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_handle_profile_unknown_sub():
    tui = _make_tui()
    tui._handle_profile(["unknown"])


def test_tui_handle_invariants_list_empty():
    tui = _make_tui()
    tui.invariants = []
    tui._handle_invariants(["list"])


def test_tui_handle_invariants_list_with_items():
    tui = _make_tui()
    tui.invariants = ["No RxJava", "Only Kotlin"]
    tui._handle_invariants(["list"])


def test_tui_handle_invariants_add(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.INVARIANTS_DIR
    cfg.INVARIANTS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui.invariants = []
        tui._handle_invariants(["add", "No", "Java"])
        assert "No Java" in tui.invariants
    finally:
        cfg.INVARIANTS_DIR = orig


def test_tui_handle_invariants_add_via_prompt(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.INVARIANTS_DIR
    cfg.INVARIANTS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui.invariants = []
        with patch.object(tui, "_prompt", return_value="Only Rust"):
            tui._handle_invariants(["add"])
        assert "Only Rust" in tui.invariants
    finally:
        cfg.INVARIANTS_DIR = orig


def test_tui_handle_invariants_add_empty_prompt(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.INVARIANTS_DIR
    cfg.INVARIANTS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui.invariants = []
        with patch.object(tui, "_prompt", return_value=""):
            tui._handle_invariants(["add"])
        assert tui.invariants == []
    finally:
        cfg.INVARIANTS_DIR = orig


def test_tui_handle_invariants_unknown_sub():
    tui = _make_tui()
    tui._handle_invariants(["unknown"])


def _mock_chat_with_stats(text: str):
    """Return a side_effect for chat_with_stats that yields (text, TokenUsage)."""
    from agent_cli.llm.provider import TokenUsage
    return (text, TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_rub=0.005))


def test_tui_chat_no_invariants():
    from agent_cli.llm.provider import LLMProvider
    tui = _make_tui()
    mock = MagicMock(spec=LLMProvider)
    mock.chat_with_stats.return_value = _mock_chat_with_stats("Response text")
    tui.agent.provider = mock
    tui.invariants = []
    tui._chat("Hello")
    mock.chat_with_stats.assert_called_once()


def test_tui_chat_invariant_ok():
    from agent_cli.llm.provider import LLMProvider
    tui = _make_tui()
    mock = MagicMock(spec=LLMProvider)
    # chat_with_stats for agent; chat for invariant checker
    mock.chat_with_stats.return_value = _mock_chat_with_stats("Safe response.")
    mock.chat.return_value = "ОК"
    tui.provider = mock        # checker uses tui.provider
    tui.agent.provider = mock  # agent also uses mock
    tui.invariants = ["No RxJava"]
    tui._chat("question")
    # Memory should have grown (exchange kept — not rolled back)
    assert len(tui.agent.memory.short_term) == 2


def test_tui_chat_invariant_violated():
    from agent_cli.llm.provider import LLMProvider
    tui = _make_tui()
    mock = MagicMock(spec=LLMProvider)
    mock.chat_with_stats.return_value = _mock_chat_with_stats("Here is RxJava code.")
    mock.chat.return_value = "НАРУШЕНИЕ: нарушен инвариант No RxJava"
    tui.provider = mock
    tui.agent.provider = mock
    tui.invariants = ["No RxJava"]
    tui._chat("write something")
    # Memory should be rolled back (pop_last_exchange)
    assert len(tui.agent.memory.short_term) == 0
    # session_stats rolled back too
    assert tui.agent.session_stats.calls == 0


def test_tui_handle_task_start(tmp_path):
    from agent_cli.llm.provider import LLMProvider
    from agent_cli.state.machine import VALIDATION_OK_MARKER
    import agent_cli.config as cfg

    responses = [
        "Plan. <<ПЛАН ГОТОВ>>",
        "Done. <<ВЫПОЛНЕНО>>",
        f"OK. {VALIDATION_OK_MARKER}",
    ]
    call_idx = {"i": 0}

    def fake_chat(messages, model, **kwargs):
        r = responses[min(call_idx["i"], len(responses) - 1)]
        call_idx["i"] += 1
        return r

    mock = MagicMock(spec=LLMProvider)
    mock.chat.side_effect = fake_chat

    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui.agent.provider = mock
        tui.provider = mock
        # Patch coordinator to avoid real calls from TUI
        with patch("agent_cli.tui.TaskCoordinator") as MockCoord:
            instance = MockCoord.return_value
            from agent_cli.state.coordinator import TaskState
            from agent_cli.state.machine import Stage
            done_task = TaskState("x001", "Сделай X")
            done_task.stage = Stage.DONE
            instance.run.return_value = done_task
            tui._handle_task(["start", "Сделай", "X"])
        assert tui.current_task is not None
    finally:
        cfg.TASKS_DIR = orig


def test_tui_handle_task_start_prompt(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        with patch("agent_cli.tui.TaskCoordinator") as MockCoord:
            from agent_cli.state.coordinator import TaskState
            from agent_cli.state.machine import Stage
            done_task = TaskState("x002", "Prompted task")
            done_task.stage = Stage.DONE
            MockCoord.return_value.run.return_value = done_task
            with patch.object(tui, "_prompt", return_value="Prompted task"):
                tui._handle_task(["start"])
    finally:
        cfg.TASKS_DIR = orig


def test_tui_handle_task_start_empty_prompt(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        with patch.object(tui, "_prompt", return_value=""):
            tui._handle_task(["start"])
        assert tui.current_task is None
    finally:
        cfg.TASKS_DIR = orig


def test_tui_handle_task_resume_no_task(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        tui.current_task = None
        tui._handle_task(["resume"])  # no task, no crash
    finally:
        cfg.TASKS_DIR = orig


def test_tui_handle_task_resume_existing(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.state.coordinator import TaskState
    from agent_cli.state.machine import Stage

    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = str(tmp_path)
    try:
        saved = TaskState("r001", "Resume me")
        saved.stage = Stage.EXECUTION
        saved.plan = "Some plan"
        saved.save()

        tui = _make_tui()
        tui.current_task = saved
        with patch("agent_cli.tui.TaskCoordinator") as MockCoord:
            done_task = TaskState("r001", "Resume me")
            done_task.stage = Stage.DONE
            MockCoord.return_value.run.return_value = done_task
            tui._handle_task(["resume"])
        assert tui.current_task.stage == Stage.DONE
    finally:
        cfg.TASKS_DIR = orig


def test_tui_handle_task_unknown_sub():
    tui = _make_tui()
    tui._handle_task(["unknown"])


def test_tui_prompt_fallback_no_session():
    """_prompt falls back to input() when no session."""
    tui = _make_tui()
    tui.session = None
    with patch("builtins.input", return_value="test_value"):
        result = tui._prompt("Enter: ")
    assert result == "test_value"


def test_tui_prompt_uses_session():
    """_prompt uses session.prompt() when session set."""
    tui = _make_tui()
    mock_session = MagicMock()
    mock_session.prompt.return_value = "from_session"
    tui.session = mock_session
    result = tui._prompt("Q: ")
    assert result == "from_session"
    mock_session.prompt.assert_called_once_with("Q: ")


def test_tui_make_agent_with_profile():
    tui = _make_tui()
    from agent_cli.profile.profile import UserProfile
    tui.current_profile = UserProfile(name="x", style="Short")
    tui.invariants = ["rule1"]
    agent = tui._make_agent()
    assert "Short" in agent.profile_content
    assert "rule1" in agent.invariants


def test_tui_toolbar_no_task_no_profile():
    tui = _make_tui()
    tui.current_profile = None
    tui.current_task = None
    result = tui._toolbar()
    html = str(result)
    assert "no profile" in html
    assert "—" in html


def test_tui_toolbar_with_profile_and_task():
    from agent_cli.profile.profile import UserProfile
    from agent_cli.state.coordinator import TaskState
    from agent_cli.state.machine import Stage
    tui = _make_tui()
    tui.current_profile = UserProfile(name="myprofile")
    task = TaskState("t1", "q")
    task.stage = Stage.EXECUTION
    tui.current_task = task
    result = tui._toolbar()
    html = str(result)
    assert "myprofile" in html
    assert "execution" in html


def test_tui_make_coordinator_uses_profile_and_model():
    from agent_cli.profile.profile import UserProfile
    tui = _make_tui()
    tui.current_profile = UserProfile(name="p", stack="Kotlin")
    tui.model = "some-model"
    tui.invariants = ["no java"]
    coord = tui._make_coordinator()
    assert coord.model == "some-model"
    assert "Kotlin" in coord.profile_content
    assert "no java" in coord.invariants


# ── missing branches: profile/coordinator non-existent dirs ───────────────────

def test_profile_to_prompt_text_persona_rules_interests():
    from agent_cli.profile.profile import UserProfile
    p = UserProfile(name="x", persona="Senior Dev", rules="No RxJava", interests="Open Source")
    text = p.to_prompt_text()
    assert "Senior Dev" in text
    assert "No RxJava" in text
    assert "Open Source" in text
    assert "Профиль" in text
    assert "Правила" in text
    assert "Увлечения" in text


def test_profile_list_all_nonexistent_dir():
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = "/tmp/__nonexistent_profiles_xyz__"
    try:
        result = UserProfile.list_all()
        assert result == []
    finally:
        cfg.PROFILES_DIR = orig


def test_task_state_latest_no_dir():
    import agent_cli.config as cfg
    from agent_cli.state.coordinator import TaskState
    orig = cfg.TASKS_DIR
    cfg.TASKS_DIR = "/tmp/__nonexistent_tasks_xyz__"
    try:
        result = TaskState.latest()
        assert result is None
    finally:
        cfg.TASKS_DIR = orig


# ── tui.py run() loop ──────────────────────────────────────────────────────────

def _run_tui_with_inputs(inputs: list[str], tmp_path=None):
    """Run TUI REPL with a scripted list of inputs, returns the TUI instance."""
    import agent_cli.config as cfg
    import tempfile

    tmp = tmp_path or tempfile.mkdtemp()
    orig_tasks = cfg.TASKS_DIR
    orig_invs = cfg.INVARIANTS_DIR
    cfg.TASKS_DIR = str(tmp)
    cfg.INVARIANTS_DIR = str(tmp)

    inputs_iter = iter(inputs)

    class FakeSession:
        def __init__(self, *a, **kw):
            pass
        def prompt(self, *a, **kw):
            try:
                return next(inputs_iter)
            except StopIteration:
                raise EOFError

    try:
        tui = _make_tui()
        with patch("agent_cli.tui.PromptSession", FakeSession):
            tui.run()
    finally:
        cfg.TASKS_DIR = orig_tasks
        cfg.INVARIANTS_DIR = orig_invs

    return tui


def test_tui_run_exits_on_exit():
    tui = _run_tui_with_inputs(["/exit"])
    assert tui is not None


def test_tui_run_exits_on_quit():
    _run_tui_with_inputs(["/quit"])


def test_tui_run_exits_on_eof():
    _run_tui_with_inputs([])  # StopIteration → EOFError → break


def test_tui_run_exits_on_keyboard_interrupt():
    tui = _make_tui()
    import agent_cli.config as cfg
    import tempfile
    tmp = tempfile.mkdtemp()
    orig_tasks, orig_invs = cfg.TASKS_DIR, cfg.INVARIANTS_DIR
    cfg.TASKS_DIR = cfg.INVARIANTS_DIR = tmp

    class InterruptSession:
        def __init__(self, *a, **kw): pass
        def prompt(self, *a, **kw): raise KeyboardInterrupt

    try:
        with patch("agent_cli.tui.PromptSession", InterruptSession):
            tui.run()
    finally:
        cfg.TASKS_DIR, cfg.INVARIANTS_DIR = orig_tasks, orig_invs


def test_tui_run_skip_empty_input():
    _run_tui_with_inputs(["", "  ", "/exit"])


def test_tui_run_help_command():
    _run_tui_with_inputs(["/help", "/exit"])


def test_tui_run_clear_command():
    _run_tui_with_inputs(["/clear", "/exit"])


def test_tui_run_model_show():
    tui = _run_tui_with_inputs(["/model", "/exit"])
    assert tui.model == "openai/gpt-4o-mini"


def test_tui_run_model_change():
    tui = _run_tui_with_inputs(["/model test-model", "/exit"])
    assert tui.model == "test-model"


def test_tui_run_state_no_task():
    _run_tui_with_inputs(["/state", "/exit"])


def test_tui_run_state_with_task():
    from agent_cli.state.coordinator import TaskState
    from agent_cli.state.machine import Stage
    tui_holder = {}

    def side_effect_run(inputs):
        import agent_cli.config as cfg, tempfile
        tmp = tempfile.mkdtemp()
        orig_tasks, orig_invs = cfg.TASKS_DIR, cfg.INVARIANTS_DIR
        cfg.TASKS_DIR = cfg.INVARIANTS_DIR = tmp
        inputs_iter = iter(inputs)

        class FakeSession:
            def __init__(self, *a, **kw): pass
            def prompt(self, *a, **kw):
                try: return next(inputs_iter)
                except StopIteration: raise EOFError

        tui = _make_tui()
        task = TaskState("t1", "My task")
        task.stage = Stage.EXECUTION
        tui.current_task = task
        try:
            with patch("agent_cli.tui.PromptSession", FakeSession):
                tui.run()
        finally:
            cfg.TASKS_DIR, cfg.INVARIANTS_DIR = orig_tasks, orig_invs
        return tui

    result = side_effect_run(["/state", "/exit"])
    assert result.current_task is not None


def test_tui_run_profile_command():
    _run_tui_with_inputs(["/profile list", "/exit"])


def test_tui_run_invariants_command():
    _run_tui_with_inputs(["/invariants list", "/exit"])


def test_tui_run_unknown_command():
    _run_tui_with_inputs(["/unknowncmd", "/exit"])


def test_tui_run_chat_no_invariants():
    from agent_cli.llm.provider import LLMProvider
    import agent_cli.config as cfg
    import tempfile

    tmp = tempfile.mkdtemp()
    orig_tasks, orig_invs = cfg.TASKS_DIR, cfg.INVARIANTS_DIR
    cfg.TASKS_DIR = cfg.INVARIANTS_DIR = tmp

    inputs = iter(["say something", "/exit"])

    class FakeSession:
        def __init__(self, *a, **kw): pass
        def prompt(self, *a, **kw):
            try: return next(inputs)
            except StopIteration: raise EOFError

    from agent_cli.llm.provider import TokenUsage
    mock = MagicMock(spec=LLMProvider)
    mock.chat_with_stats.return_value = ("I said something.", TokenUsage(prompt_tokens=10, completion_tokens=5))

    try:
        tui = _make_tui()
        tui.provider = mock
        tui.agent.provider = mock
        with patch("agent_cli.tui.PromptSession", FakeSession):
            tui.run()
    finally:
        cfg.TASKS_DIR, cfg.INVARIANTS_DIR = orig_tasks, orig_invs


def test_tui_handle_profile_edit_no_profile():
    tui = _make_tui()
    tui.current_profile = None
    tui._handle_profile(["edit"])  # should print warning, no crash


def test_tui_handle_profile_edit_with_profile():
    from agent_cli.profile.profile import UserProfile
    tui = _make_tui()
    tui.current_profile = UserProfile(name="myp", style="Brief")
    with patch("os.system") as mock_sys:
        tui._handle_profile(["edit"])
    mock_sys.assert_called_once()


# ── token usage & pricing ─────────────────────────────────────────────────────

def test_token_usage_str():
    from agent_cli.llm.provider import TokenUsage
    u = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150,
                   elapsed_ms=1200.0, cost_rub=0.0025)
    s = str(u)
    assert "100" in s
    assert "50" in s
    assert "150" in s
    assert "1200" in s
    assert "0.0025" in s


def test_session_stats_add_and_total():
    from agent_cli.llm.provider import TokenUsage, SessionStats
    stats = SessionStats()
    assert stats.total_tokens == 0
    assert stats.calls == 0

    stats.add(TokenUsage(prompt_tokens=100, completion_tokens=50, cost_rub=0.01))
    stats.add(TokenUsage(prompt_tokens=200, completion_tokens=80, cost_rub=0.02))

    assert stats.prompt_tokens == 300
    assert stats.completion_tokens == 130
    assert stats.total_tokens == 430
    assert abs(stats.cost_rub - 0.03) < 1e-9
    assert stats.calls == 2


def test_config_get_pricing_known_model():
    from agent_cli.config import get_pricing
    p = get_pricing("openai/gpt-4o-mini")
    assert p["input"] == 0.015
    assert p["output"] == 0.06


def test_config_get_pricing_unknown_model():
    from agent_cli.config import get_pricing, _DEFAULT_PRICING
    p = get_pricing("some/unknown-model-xyz")
    assert p == _DEFAULT_PRICING


def test_config_calc_cost_rub():
    from agent_cli.config import calc_cost_rub
    # gpt-4o-mini: 1000 input × 0.015/1K + 500 output × 0.06/1K = 0.015 + 0.030 = 0.045
    cost = calc_cost_rub(1000, 500, "openai/gpt-4o-mini")
    assert abs(cost - 0.045) < 1e-9


def test_proxyapi_chat_with_stats():
    from agent_cli.llm.proxyapi import ProxyAPIProvider
    from agent_cli.llm.provider import TokenUsage

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 120
    mock_usage.completion_tokens = 60
    mock_usage.total_tokens = 180

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hello stats"
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        provider = ProxyAPIProvider()
        text, usage = provider.chat_with_stats([{"role": "user", "content": "hi"}], "openai/gpt-4o-mini")

    assert text == "Hello stats"
    assert usage.prompt_tokens == 120
    assert usage.completion_tokens == 60
    assert usage.total_tokens == 180
    assert usage.elapsed_ms > 0
    assert usage.cost_rub > 0  # 120 * 0.015/1000 + 60 * 0.06/1000


def test_proxyapi_chat_with_stats_no_usage():
    """When API returns no usage, stats are zero."""
    from agent_cli.llm.proxyapi import ProxyAPIProvider

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "ok"
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        provider = ProxyAPIProvider()
        text, usage = provider.chat_with_stats([], "openai/gpt-4o-mini")

    assert text == "ok"
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0


def test_agent_respond_with_stats_mock():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider, TokenUsage

    mock = MagicMock(spec=LLMProvider)
    mock.chat_with_stats.return_value = ("answer", TokenUsage(
        prompt_tokens=80, completion_tokens=40, total_tokens=120, cost_rub=0.003
    ))

    agent = Agent(provider=mock, model="test")
    text, usage = agent.respond_with_stats("question")

    assert text == "answer"
    assert usage.prompt_tokens == 80
    assert usage.cost_rub == 0.003
    assert agent.session_stats.calls == 1
    assert agent.session_stats.prompt_tokens == 80
    assert agent.session_stats.total_tokens == 120
    assert len(agent.memory.short_term) == 2


def test_tui_stats_line():
    from agent_cli.llm.provider import TokenUsage
    tui = _make_tui()
    usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150,
                       elapsed_ms=800.0, cost_rub=0.0025)
    line = tui._stats_line(usage)
    assert "100" in line
    assert "50" in line
    assert "150" in line
    assert "0.0025" in line
    assert "800" in line


def test_tui_toolbar_shows_token_stats():
    tui = _make_tui()
    from agent_cli.llm.provider import TokenUsage
    tui.agent.session_stats.add(TokenUsage(
        prompt_tokens=200, completion_tokens=100, total_tokens=300, cost_rub=0.015
    ))
    result = str(tui._toolbar())
    assert "300tok" in result
    assert "0.0150" in result


def test_llm_provider_default_chat_with_stats():
    """Default chat_with_stats() wraps chat() with timing."""
    from agent_cli.llm.provider import LLMProvider, TokenUsage
    from typing import Iterator
    import time

    class MinimalProvider(LLMProvider):
        def chat(self, messages, model, **kwargs) -> str:
            return "default_response"
        def chat_stream(self, messages, model, **kwargs) -> Iterator[str]:
            yield "x"

    p = MinimalProvider()
    text, usage = p.chat_with_stats([{"role": "user", "content": "hi"}], "m")
    assert text == "default_response"
    assert usage.elapsed_ms >= 0
    assert usage.prompt_tokens == 0  # no real usage in default impl


def test_tui_profile_onboard(tmp_path):
    import agent_cli.config as cfg
    from agent_cli.profile.profile import UserProfile

    orig_profiles = cfg.PROFILES_DIR
    orig_invs = cfg.INVARIANTS_DIR
    cfg.PROFILES_DIR = str(tmp_path / "profiles")
    cfg.INVARIANTS_DIR = str(tmp_path / "invs")
    import os; os.makedirs(cfg.PROFILES_DIR, exist_ok=True)

    answers = iter([
        "athlete_profile",         # name
        "Спортсмен, бегун",        # persona
        "Дружелюбно, с поддержкой",  # style
        "Без нудных лекций",       # rules
        "Не технарь",              # stack
    ])

    try:
        tui = _make_tui()
        # mock extractor to avoid real LLM call
        with patch("agent_cli.profile.extractor.route_fact", return_value="persona"), \
             patch.object(tui, "_prompt", side_effect=lambda _: next(answers, "")):
            tui._profile_onboard()

        assert tui.current_profile is not None
        assert tui.current_profile.name == "athlete_profile"
        profile_file = tmp_path / "profiles" / "athlete_profile.md"
        assert profile_file.exists()
    finally:
        cfg.PROFILES_DIR = orig_profiles
        cfg.INVARIANTS_DIR = orig_invs


def test_tui_profile_onboard_no_name(tmp_path):
    """If name is empty after prompt, onboard aborts."""
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        with patch.object(tui, "_prompt", return_value=""):
            tui._profile_onboard()
        assert tui.current_profile is None
    finally:
        cfg.PROFILES_DIR = orig


def test_tui_profile_create_command(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        tui = _make_tui()
        with patch.object(tui, "_profile_onboard") as mock_onboard:
            tui._handle_profile(["create", "myname"])
        mock_onboard.assert_called_once_with("myname")
    finally:
        cfg.PROFILES_DIR = orig


# ── proxyapi chat_stream_with_stats + TokenUsageRef ───────────────────────────

def test_proxyapi_chat_stream_with_stats():
    from agent_cli.llm.proxyapi import ProxyAPIProvider

    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "hello"
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter([chunk_content, chunk_usage])

    with patch("agent_cli.llm.proxyapi.OpenAI", return_value=mock_client):
        provider = ProxyAPIProvider()
        gen, ref = provider.chat_stream_with_stats([{"role": "user", "content": "hi"}], "openai/gpt-4o-mini")
        chunks = list(gen)

    assert chunks == ["hello"]
    usage = ref.usage
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 5
    assert usage.total_tokens == 15
    assert usage.cost_rub >= 0


def test_token_usage_ref_usage_property():
    from agent_cli.llm.proxyapi import TokenUsageRef
    ref = TokenUsageRef("openai/gpt-4o-mini")
    ref.prompt_tokens = 100
    ref.completion_tokens = 50
    ref.total_tokens = 150
    ref.elapsed_ms = 500.0
    u = ref.usage
    assert u.prompt_tokens == 100
    assert u.completion_tokens == 50
    assert u.total_tokens == 150
    assert u.elapsed_ms == 500.0
    assert u.cost_rub >= 0


# ── core/memory take_old_for_summary ─────────────────────────────────────────

def test_memory_take_old_for_summary():
    from agent_cli.core.memory import Memory, SUMMARIZE_AT, KEEP_RECENT
    m = Memory()
    for i in range(SUMMARIZE_AT):
        m.add_message("user", f"msg{i}")
    assert m.needs_summary()
    old = m.take_old_for_summary()
    assert len(old) == SUMMARIZE_AT - KEEP_RECENT
    assert len(m.short_term) == KEEP_RECENT


def test_memory_take_old_too_few():
    from agent_cli.core.memory import Memory, KEEP_RECENT
    m = Memory()
    for i in range(KEEP_RECENT - 1):
        m.add_message("user", f"msg{i}")
    old = m.take_old_for_summary()
    assert old == []


# ── core/agent _try_summarize ─────────────────────────────────────────────────

def _make_mock_proxyapi():
    """Return a mock that looks like ProxyAPIProvider."""
    from agent_cli.llm.proxyapi import ProxyAPIProvider
    from agent_cli.llm.provider import TokenUsage
    mock = MagicMock(spec=ProxyAPIProvider)
    mock.chat.return_value = "резюме"
    mock.chat_with_stats.return_value = ("reply", TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10))
    return mock


def test_agent_try_summarize_triggers():
    from agent_cli.core.agent import Agent
    from agent_cli.core.memory import SUMMARIZE_AT
    mock = _make_mock_proxyapi()
    agent = Agent(provider=mock, model="openai/gpt-4o-mini")
    for i in range(SUMMARIZE_AT):
        agent.memory.add_message("user", f"q{i}")
        agent.memory.add_message("assistant", f"a{i}")
    # Now force summarize
    agent._try_summarize()
    assert agent.memory.summary != ""
    mock.chat.assert_called()


def test_agent_try_summarize_with_existing_summary():
    from agent_cli.core.agent import Agent
    from agent_cli.core.memory import SUMMARIZE_AT
    mock = _make_mock_proxyapi()
    agent = Agent(provider=mock, model="openai/gpt-4o-mini")
    agent.memory.summary = "старое резюме"
    for i in range(SUMMARIZE_AT):
        agent.memory.add_message("user", f"q{i}")
        agent.memory.add_message("assistant", f"a{i}")
    agent._try_summarize()
    assert "старое резюме" in agent.memory.summary


def test_agent_try_summarize_not_needed():
    from agent_cli.core.agent import Agent
    mock = _make_mock_proxyapi()
    agent = Agent(provider=mock, model="openai/gpt-4o-mini")
    agent.memory.add_message("user", "one msg")
    agent._try_summarize()
    # chat() for summarization should NOT be called
    mock.chat.assert_not_called()


# ── core/agent respond_stream_with_stats (ProxyAPI path + fallback) ──────────

def test_agent_respond_stream_with_stats_proxyapi():
    from agent_cli.core.agent import Agent
    from agent_cli.llm.proxyapi import ProxyAPIProvider, TokenUsageRef
    from agent_cli.llm.provider import TokenUsage

    mock = MagicMock(spec=ProxyAPIProvider)
    ref = TokenUsageRef("openai/gpt-4o-mini")
    ref.prompt_tokens = 10
    ref.completion_tokens = 5
    ref.total_tokens = 15
    mock.chat_stream_with_stats.return_value = (iter(["hello", " world"]), ref)

    agent = Agent(provider=mock, model="openai/gpt-4o-mini")
    gen, ret_ref = agent.respond_stream_with_stats("hi")
    chunks = list(gen)

    assert chunks == ["hello", " world"]
    assert agent.memory.short_term[-2]["content"] == "hi"
    assert agent.memory.short_term[-1]["content"] == "hello world"
    assert agent.session_stats.calls == 1


def test_agent_respond_stream_with_stats_fallback():
    """Non-ProxyAPI provider uses respond_with_stats fallback."""
    from agent_cli.core.agent import Agent
    from agent_cli.llm.provider import LLMProvider, TokenUsage
    from typing import Iterator

    class DummyProvider(LLMProvider):
        def chat(self, messages, model, **kwargs) -> str:
            return "dummy"
        def chat_stream(self, messages, model, **kwargs) -> Iterator[str]:
            yield "dummy"
        def chat_with_stats(self, messages, model, **kwargs):
            return "dummy", TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)

    agent = Agent(provider=DummyProvider(), model="openai/gpt-4o-mini")
    gen, ref = agent.respond_stream_with_stats("test")
    chunks = list(gen)
    assert chunks == ["dummy"]
    usage = ref.usage
    assert usage.total_tokens == 2


# ── tui _confirm_fn ───────────────────────────────────────────────────────────

def _make_tui_bare():
    with patch("agent_cli.llm.proxyapi.OpenAI"):
        from agent_cli.tui import TUI
        return TUI()


def test_confirm_fn_yes():
    tui = _make_tui_bare()
    with patch.object(tui, "_prompt", return_value="y"):
        assert tui._confirm_fn("Продолжить?") is True


def test_confirm_fn_da():
    tui = _make_tui_bare()
    with patch.object(tui, "_prompt", return_value="да"):
        assert tui._confirm_fn("Продолжить?") is True


def test_confirm_fn_no():
    tui = _make_tui_bare()
    with patch.object(tui, "_prompt", return_value="n"):
        assert tui._confirm_fn("Продолжить?") is False


# ── tui _profile_onboard empty answer skips ───────────────────────────────────

def test_profile_onboard_empty_answer_skips(tmp_path):
    import agent_cli.config as cfg
    orig = cfg.PROFILES_DIR
    cfg.PROFILES_DIR = str(tmp_path)
    try:
        tui = _make_tui_bare()
        # name is pre-supplied; 4 question prompts follow
        answers = iter(["", "style answer", "", "stack stuff"])
        with patch.object(tui, "_prompt", side_effect=lambda _: next(answers)), \
             patch("agent_cli.profile.extractor.route_fact", return_value="style"):
            tui._profile_onboard("testuser")
        assert tui.current_profile is not None
        assert "style answer" in tui.current_profile.style
    finally:
        cfg.PROFILES_DIR = orig


# ── tui _handle_task unknown subcommand ───────────────────────────────────────

def test_handle_task_unknown_sub():
    tui = _make_tui_bare()
    from io import StringIO
    with patch("agent_cli.tui.console") as mock_console:
        tui._handle_task(["unknown"])
        mock_console.print.assert_called()


# ── provider abstract pass bodies ────────────────────────────────────────────

def test_provider_abstract_bodies_not_callable():
    """Abstract methods are pass-stubs; concrete subclasses override them."""
    from agent_cli.llm.provider import LLMProvider
    from typing import Iterator

    # This just ensures the lines are imported / covered by subclass test above
    class MinimalProvider(LLMProvider):
        def chat(self, messages, model, **kwargs) -> str:
            return super().chat(messages, model, **kwargs) or ""  # calls pass
        def chat_stream(self, messages, model, **kwargs) -> Iterator[str]:
            result = super().chat_stream(messages, model, **kwargs)
            return iter([]) if result is None else result

    p = MinimalProvider()
    assert p.chat([], "m") == ""
    assert list(p.chat_stream([], "m")) == []
