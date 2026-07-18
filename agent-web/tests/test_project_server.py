"""Day 31: mcp-server/project_server.py — pure-function tests on a temp git repo.
No network, no real server started. Same import-by-sys.path pattern as
mcp-server/test_server.py (that dir has no package structure of its own)."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-server"))


def _reload_project_server(project_root: Path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    if "project_server" in sys.modules:
        del sys.modules["project_server"]
    import project_server
    return project_server


def _init_git_repo(path: Path, branch: str = "main"):
    subprocess.run(["git", "init", "-b", branch], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


@pytest.fixture
def git_repo(tmp_path):
    _init_git_repo(tmp_path)
    return tmp_path


def test_git_current_branch(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    assert ps.git_current_branch() == "main"


def test_git_current_branch_after_checkout(git_repo, monkeypatch):
    subprocess.run(["git", "checkout", "-b", "feature/day-31"], cwd=git_repo, capture_output=True, check=True)
    ps = _reload_project_server(git_repo, monkeypatch)
    assert ps.git_current_branch() == "feature/day-31"


def test_git_status_clean(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    assert ps.git_status() == "working tree clean"


def test_git_status_dirty(git_repo, monkeypatch):
    (git_repo / "new_file.txt").write_text("x", encoding="utf-8")
    ps = _reload_project_server(git_repo, monkeypatch)
    assert "new_file.txt" in ps.git_status()


def test_list_project_files_lists_repo_root(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_project_files()
    assert "README.md" in out


def test_list_project_files_cannot_escape_via_dotdot(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_project_files(subdir="../../../../etc")
    assert "escapes the project root" in out


def test_list_project_files_cannot_escape_via_absolute_path(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_project_files(subdir="/etc")
    assert "escapes the project root" in out


def test_list_project_files_hides_env_and_git(git_repo, monkeypatch):
    (git_repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_project_files(pattern="*")
    assert ".env" not in out
    assert ".git" not in out


def test_list_project_files_nonexistent_subdir(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_project_files(subdir="does-not-exist")
    assert "does not exist" in out


# ── Day 33: list_tickets / get_ticket ──────────────────────────────────────
import json  # noqa: E402


def _seed_tickets(git_repo: Path, tickets: list[dict]):
    tickets_dir = git_repo / "agent-web" / "data" / "support"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / "tickets.json").write_text(json.dumps(tickets), encoding="utf-8")


def _fake_ticket(id="TICKET-001", status="resolved", environment="Windows 11, SOCKS proxy"):
    return {
        "id": id, "title": "test ticket", "product_area": "x", "version": "1.0",
        "environment": environment, "symptom": "s", "steps": ["a"], "status": status,
        "user": "u", "history": [{"author": "u", "text": "t"}],
    }


def test_list_tickets_all(git_repo, monkeypatch):
    _seed_tickets(git_repo, [_fake_ticket("TICKET-001"), _fake_ticket("TICKET-002", status="open")])
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_tickets()
    assert "TICKET-001" in out
    assert "TICKET-002" in out


def test_list_tickets_filtered_by_status(git_repo, monkeypatch):
    _seed_tickets(git_repo, [_fake_ticket("TICKET-001", status="resolved"), _fake_ticket("TICKET-002", status="open")])
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_tickets(status="open")
    assert "TICKET-002" in out
    assert "TICKET-001" not in out


def test_list_tickets_empty_when_no_file(git_repo, monkeypatch):
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.list_tickets()
    assert "no tickets" in out


def test_get_ticket_found_returns_full_json(git_repo, monkeypatch):
    _seed_tickets(git_repo, [_fake_ticket("TICKET-001", environment="Windows 11, SOCKS proxy enabled")])
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.get_ticket("TICKET-001")
    data = json.loads(out)
    assert data["id"] == "TICKET-001"
    assert data["environment"] == "Windows 11, SOCKS proxy enabled"


def test_get_ticket_not_found(git_repo, monkeypatch):
    _seed_tickets(git_repo, [_fake_ticket("TICKET-001")])
    ps = _reload_project_server(git_repo, monkeypatch)
    out = ps.get_ticket("TICKET-999")
    assert "not found" in out
