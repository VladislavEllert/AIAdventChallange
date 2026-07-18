"""Day 34: fs_tools sandbox — SECURITY test, exhaustive per plan.

REPO_ROOT is resolved at import time from the PROJECT_ROOT env var, so each
test reloads the module against a fresh tmp_path "fake repo" (same pattern as
tests/test_project_server.py for mcp-server/project_server.py).
"""
import importlib
import os

import pytest

import agent_web.services.tools.registry as _registry_mod
import agent_web.services.tools.fs_tools as _fs_tools_mod


def _reload_fs_tools(project_root, monkeypatch):
    # NB: sys.modules.pop() + `from pkg import submodule` does NOT force a real
    # reload here — Python's IMPORT_FROM opcode does getattr(pkg, name) first
    # and finds the STALE attribute the parent package already cached, never
    # touching sys.modules again. importlib.reload() is the only way that
    # actually re-executes the module body (and re-reads PROJECT_ROOT).
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    importlib.reload(_registry_mod)
    importlib.reload(_fs_tools_mod)
    return _fs_tools_mod


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.txt").write_text("hello\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / "id.key").write_text("privatekey\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("x", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("x", encoding="utf-8")
    return tmp_path


# ── escaping REPO_ROOT ─────────────────────────────────────────────────────

def test_absolute_path_outside_repo_rejected(repo, monkeypatch, tmp_path_factory):
    fs = _reload_fs_tools(repo, monkeypatch)
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox(str(outside))


def test_dotdot_traversal_rejected(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox("../../../../../../etc/passwd")


def test_dotdot_traversal_relative_style(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox("sub/../../outside.txt")


def test_symlink_escaping_repo_rejected(repo, monkeypatch, tmp_path_factory):
    fs = _reload_fs_tools(repo, monkeypatch)
    outside_dir = tmp_path_factory.mktemp("outside_link")
    secret = outside_dir / "secret.txt"
    secret.write_text("nope", encoding="utf-8")
    link = repo / "escape_link"
    os.symlink(outside_dir, link)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox("escape_link/secret.txt")


# ── forbidden denylist, even INSIDE the repo ───────────────────────────────

def test_env_file_blocked(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox(".env")


def test_key_file_blocked(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox("id.key")


def test_git_dir_blocked(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox(".git/config")


def test_venv_dir_blocked(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox(".venv/pyvenv.cfg")


def test_node_modules_blocked(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs.resolve_in_sandbox("node_modules/pkg.js")


# ── legitimate in-sandbox access still works ────────────────────────────────

def test_read_file_inside_sandbox_ok(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    assert fs._read_file("sub/file.txt") == "hello\n"


def test_read_file_error_paths_return_string_not_raise(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    assert "does not exist" in fs._read_file("nope.txt")
    assert "directory" in fs._read_file("sub")


def test_list_dir_excludes_forbidden(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    out = fs._list_dir(".")
    assert ".env" not in out
    assert "id.key" not in out
    assert ".git" not in out
    assert ".venv" not in out
    assert "node_modules" not in out
    assert "sub/" in out


def test_write_file_dry_run_default_does_not_write(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    target = repo / "new.txt"
    result = fs._write_file("new.txt", "content")
    assert "DRY RUN" in result
    assert not target.exists()


def test_write_file_real_write_mode(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    target = repo / "new.txt"
    result = fs._write_file("new.txt", "content", dry_run=False)
    assert "Wrote" in result
    assert target.read_text(encoding="utf-8") == "content"


def test_write_file_refuses_env(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs._write_file(".env", "pwned", dry_run=False)


def test_delete_file_refuses_key(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    with pytest.raises(fs.SandboxError):
        fs._delete_file("id.key")


def test_delete_file_removes_in_sandbox_file(repo, monkeypatch):
    fs = _reload_fs_tools(repo, monkeypatch)
    target = repo / "sub" / "file.txt"
    assert target.exists()
    result = fs._delete_file("sub/file.txt")
    assert "Deleted" in result
    assert not target.exists()
