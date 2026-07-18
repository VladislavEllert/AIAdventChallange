"""Day 35: git_tools.py — read-only tools + git_commit, against a real but
temporary git repo (git operations need an actual .git, unlike fs_tools'
sandbox tests). Same reload pattern as test_fs_sandbox.py/test_tools_executor.py
since REPO_ROOT is resolved at import time from PROJECT_ROOT."""
import importlib
import subprocess

import pytest

import agent_web.services.tools.registry as _registry_mod
import agent_web.services.tools.fs_tools as _fs_tools_mod
import agent_web.services.tools.danger as _danger_mod
import agent_web.services.tools.git_tools as _git_tools_mod


def _run(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _reload_git_tools(project_root, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    importlib.reload(_registry_mod)
    importlib.reload(_fs_tools_mod)
    importlib.reload(_danger_mod)
    importlib.reload(_git_tools_mod)
    return _git_tools_mod


@pytest.fixture
def repo(tmp_path):
    _run(["init"], cwd=tmp_path)
    _run(["config", "user.email", "test@test.local"], cwd=tmp_path)
    _run(["config", "user.name", "Test"], cwd=tmp_path)
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    _run(["add", "a.txt"], cwd=tmp_path)
    _run(["commit", "-m", "initial"], cwd=tmp_path)
    return tmp_path


def test_git_tools_not_registered_except_commit(repo, monkeypatch):
    """Naming-collision avoidance: git_diff/git_log/git_status must NOT be in
    the shared registry (would collide with MCP project_server.py tool names
    of the same name — see git_tools.py module docstring)."""
    gt = _reload_git_tools(repo, monkeypatch)
    names = _registry_mod.registered_names()
    assert "git_commit" in names
    assert "git_diff" not in names
    assert "git_log" not in names
    assert "git_status" not in names


def test_git_status_clean(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    assert gt._git_status() == "(clean)"


def test_git_status_shows_dirty_file(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    (repo / "b.txt").write_text("new\n", encoding="utf-8")
    out = gt._git_status()
    assert "b.txt" in out


def test_git_diff_shows_working_tree_change(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    (repo / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    out = gt._git_diff()
    assert "world" in out


def test_git_diff_rejects_path_outside_sandbox(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    out = gt._git_diff(path="../../etc/passwd")
    assert out.startswith("Error:")


def test_git_log_shows_initial_commit(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    out = gt._git_log()
    assert "initial" in out


def test_git_commit_is_dangerous(repo, monkeypatch):
    _reload_git_tools(repo, monkeypatch)
    assert _danger_mod.danger_level("git_commit") == _danger_mod.DANGEROUS


def test_git_commit_stages_exact_paths_and_commits(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    (repo / "b.txt").write_text("new file\n", encoding="utf-8")
    (repo / "untouched.txt").write_text("should not be committed\n", encoding="utf-8")

    result = gt._git_commit("add b.txt", ["b.txt"])
    assert result.startswith("Committed")

    log = _run(["log", "-1", "--name-only", "--pretty=format:"], cwd=repo).stdout.strip()
    assert log == "b.txt"

    status = gt._git_status()
    assert "untouched.txt" in status  # still untracked — not swept in


def test_git_commit_never_sweeps_in_other_already_staged_files(repo, monkeypatch):
    """Regression: caught live during the day-35 self-test — a bare `git
    commit` (no pathspec) commits the WHOLE index, not just what was just
    staged by this call. If some OTHER file was already `git add`-ed earlier
    (a leftover stage from a prior tool run in the same session), it must
    NOT ride along into a commit that only asked for `b.txt`."""
    gt = _reload_git_tools(repo, monkeypatch)
    (repo / "b.txt").write_text("intended\n", encoding="utf-8")
    (repo / "leftover.txt").write_text("should NOT be committed\n", encoding="utf-8")
    _run(["add", "leftover.txt"], cwd=repo)  # simulates an unrelated prior stage

    result = gt._git_commit("only b.txt", ["b.txt"])
    assert result.startswith("Committed")

    log = _run(["log", "-1", "--name-only", "--pretty=format:"], cwd=repo).stdout.strip()
    assert log == "b.txt"
    assert "leftover.txt" not in log

    # leftover.txt stays exactly as staged before this call — untouched.
    status = gt._git_status()
    assert "A  leftover.txt" in status


def test_git_commit_refuses_no_paths(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    result = gt._git_commit("empty commit", [])
    assert result.startswith("Error:")


def test_git_commit_refuses_dotenv(repo, monkeypatch):
    gt = _reload_git_tools(repo, monkeypatch)
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    result = gt._git_commit("leak secret", [".env"])
    assert result.startswith("Error:")
    log = _run(["log", "--oneline"], cwd=repo).stdout
    assert "leak secret" not in log


def test_git_commit_refuses_path_outside_repo(repo, monkeypatch, tmp_path_factory):
    gt = _reload_git_tools(repo, monkeypatch)
    outside = tmp_path_factory.mktemp("outside") / "victim.txt"
    outside.write_text("x", encoding="utf-8")
    result = gt._git_commit("escape", [str(outside)])
    assert result.startswith("Error:")


def test_no_git_push_tool_exists(repo, monkeypatch):
    _reload_git_tools(repo, monkeypatch)
    assert _registry_mod.get("git_push") is None
    assert not hasattr(_git_tools_mod, "GIT_PUSH")
    assert not hasattr(_git_tools_mod, "_git_push")
