"""Day 34: tools/executor.py — danger gate + confirm handshake + real disk effects.

Two real threads (approver/denier running concurrently with the executor's
blocking `execute()`), no ASGI — same style as test_confirm.py. This is the
test that actually proves "deny -> disk untouched" and "approve -> executes"
end to end through the executor, not just the confirm registry in isolation.
"""
import importlib
import threading
import time

import pytest

import agent_web.services.tools.registry as _registry_mod
import agent_web.services.tools.danger as _danger_mod
import agent_web.services.tools.fs_tools as _fs_tools_mod
import agent_web.services.tools.executor as _executor_mod
from agent_web.services.tools import confirm as _confirm_mod


def _reload_tools(project_root, monkeypatch):
    # See test_fs_sandbox.py's _reload_fs_tools docstring — importlib.reload()
    # is required, sys.modules.pop() alone is silently ignored by `from pkg
    # import submodule` once the parent package has cached the attribute.
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    importlib.reload(_registry_mod)
    importlib.reload(_danger_mod)
    importlib.reload(_fs_tools_mod)
    importlib.reload(_executor_mod)
    _confirm_mod._reset_for_tests()
    return _registry_mod, _executor_mod, _confirm_mod


@pytest.fixture
def env(tmp_path, monkeypatch):
    return _reload_tools(tmp_path, monkeypatch)


def test_safe_tool_executes_immediately_no_confirm(env, tmp_path):
    registry, executor, confirm = env
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    result = executor.execute("read_file", {"path": "a.txt"}, stream_id="s1")
    assert result["ok"] is True
    assert result["result"] == "hi"


def test_dangerous_write_denied_leaves_disk_untouched(env, tmp_path):
    registry, executor, confirm = env
    confirm.start_session("s-deny")
    target = tmp_path / "new.txt"

    result_box = {}

    def run():
        result_box["r"] = executor.execute(
            "write_file", {"path": "new.txt", "content": "hacked", "dry_run": False},
            stream_id="s-deny", confirm_timeout=5.0, confirm_poll_interval=0.03,
        )

    t = threading.Thread(target=run)
    t.start()
    # Wait for the confirm request to be registered, then deny it.
    deadline = time.monotonic() + 2.0
    call_id = None
    while time.monotonic() < deadline and call_id is None:
        pending = confirm.list_pending()
        if pending:
            call_id = pending[0].call_id
        time.sleep(0.01)
    assert call_id is not None
    confirm.resolve(call_id, False)
    t.join(timeout=5.0)

    assert result_box["r"]["ok"] is False
    assert result_box["r"]["denied"] is True
    assert not target.exists()


def test_dangerous_write_approved_actually_writes_disk(env, tmp_path):
    registry, executor, confirm = env
    confirm.start_session("s-approve")
    target = tmp_path / "new.txt"

    result_box = {}

    def run():
        result_box["r"] = executor.execute(
            "write_file", {"path": "new.txt", "content": "real content", "dry_run": False},
            stream_id="s-approve", confirm_timeout=5.0, confirm_poll_interval=0.03,
        )

    t = threading.Thread(target=run)
    t.start()
    deadline = time.monotonic() + 2.0
    call_id = None
    while time.monotonic() < deadline and call_id is None:
        pending = confirm.list_pending()
        if pending:
            call_id = pending[0].call_id
        time.sleep(0.01)
    assert call_id is not None
    confirm.resolve(call_id, True)
    t.join(timeout=5.0)

    assert result_box["r"]["ok"] is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "real content"


def test_dangerous_write_approved_writes_even_if_llm_omitted_dry_run(env, tmp_path):
    # Regression: the LLM's tool-call arguments for write_file often omit
    # `dry_run` entirely (real gpt-4o-mini behavior, reproduced live in the
    # browser) — _write_file's own default is dry_run=True, so an approved
    # write silently no-op'd (just returned a preview string) despite the
    # human clicking "Разрешить". A human approval on the confirm modal IS
    # the real-write authorization; the executor must force dry_run=False
    # after approval, not rely on the LLM having remembered to pass it.
    registry, executor, confirm = env
    confirm.start_session("s-approve-no-dry-run")
    target = tmp_path / "new.txt"

    result_box = {}

    def run():
        result_box["r"] = executor.execute(
            "write_file", {"path": "new.txt", "content": "real content"},  # no dry_run key
            stream_id="s-approve-no-dry-run", confirm_timeout=5.0, confirm_poll_interval=0.03,
        )

    t = threading.Thread(target=run)
    t.start()
    deadline = time.monotonic() + 2.0
    call_id = None
    while time.monotonic() < deadline and call_id is None:
        pending = confirm.list_pending()
        if pending:
            call_id = pending[0].call_id
        time.sleep(0.01)
    assert call_id is not None
    confirm.resolve(call_id, True)
    t.join(timeout=5.0)

    assert result_box["r"]["ok"] is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "real content"


def test_dangerous_delete_timeout_auto_denies(env, tmp_path):
    registry, executor, confirm = env
    confirm.start_session("s-timeout")
    target = tmp_path / "victim.txt"
    target.write_text("still here", encoding="utf-8")

    result = executor.execute(
        "delete_file", {"path": "victim.txt"},
        stream_id="s-timeout", confirm_timeout=0.2, confirm_poll_interval=0.05,
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert target.exists()


def test_unknown_tool_returns_structured_error_not_raise(env):
    registry, executor, confirm = env
    result = executor.execute("does_not_exist_tool", {}, stream_id="s1")
    assert result["ok"] is False
    assert "Unknown tool" in result["result"]


def test_tool_exception_never_propagates_raw(env, tmp_path):
    registry, executor, confirm = env
    # search_files with no ripgrep-friendly args still shouldn't raise past executor
    # even in unusual conditions — force one by pointing at a path that sandbox-rejects.
    result = executor.execute("read_file", {"path": "../../outside.txt"}, stream_id="s1")
    assert result["ok"] is False
    assert "error" in result["result"].lower() or "escapes" in result["result"].lower()


def test_execute_stream_emits_confirm_request_then_keepalive_without_blocking(env, tmp_path):
    """Limited-scope SSE-shape test per plan: assert confirm_request is emitted,
    the confirm store is prefilled, and the generator doesn't block forever."""
    registry, executor, confirm = env
    confirm.start_session("s-stream")

    events = []

    def drain():
        gen = executor.execute_stream(
            "delete_file", {"path": "x.txt"}, stream_id="s-stream",
            confirm_timeout=0.3, confirm_poll_interval=0.05,
        )
        for kind, payload in gen:
            events.append((kind, payload))

    t = threading.Thread(target=drain)
    t.start()
    t.join(timeout=3.0)
    assert not t.is_alive()  # generator terminated (auto-deny on timeout), never blocked

    kinds = [k for k, _ in events]
    assert kinds[0] == "confirm_request"
    assert "tool_result" in kinds
    assert events[0][1]["tool_name"] == "delete_file"
