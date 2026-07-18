"""Day 31: build_project_corpus.py — exclusions + header parsing on a temp tree."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "rag"))
import build_project_corpus as bpc  # noqa: E402


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Minimal repo tree with files that should and shouldn't end up in the corpus."""
    (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# Claude config\n", encoding="utf-8")

    mb = tmp_path / "memory-bank"
    mb.mkdir()
    (mb / "progress.md").write_text("# progress\n", encoding="utf-8")
    lessons = mb / "lessons"
    lessons.mkdir()
    (lessons / "week-05-rag.md").write_text("# rag lesson\n", encoding="utf-8")

    week = tmp_path / "week-05" / "day-22"
    week.mkdir(parents=True)
    (week / "README.md").write_text("# day 22\n", encoding="utf-8")

    aw_pkg = tmp_path / "agent-web" / "agent_web"
    aw_pkg.mkdir(parents=True)
    (aw_pkg / "app.py").write_text("x = 1\n", encoding="utf-8")

    # excluded: .venv, node_modules, __pycache__, .env, data/rag/*.json
    venv_dir = tmp_path / "agent-web" / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "site.py").write_text("junk\n", encoding="utf-8")

    node_modules = tmp_path / "agent-web" / "frontend" / "node_modules" / "pkg"
    node_modules.mkdir(parents=True)
    (node_modules / "index.ts").write_text("junk\n", encoding="utf-8")

    pycache = aw_pkg / "__pycache__"
    pycache.mkdir()
    (pycache / "app.cpython-314.pyc").write_bytes(b"\x00\x01")

    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")

    data_rag = tmp_path / "data" / "rag"
    data_rag.mkdir(parents=True)
    (data_rag / "index_fixed.json").write_text("[]", encoding="utf-8")

    monkeypatch.setattr(bpc, "REPO_ROOT", tmp_path)
    return tmp_path


def test_excludes_venv_node_modules_pycache_env_and_index_json(fake_repo):
    files = bpc._collect()
    rels = {f.relative_to(fake_repo).as_posix() for f in files}

    assert not any(".venv" in r for r in rels)
    assert not any("node_modules" in r for r in rels)
    assert not any("__pycache__" in r for r in rels)
    assert ".env" not in rels
    assert "data/rag/index_fixed.json" not in rels


def test_excluded_rejects_data_rag_json_directly(fake_repo):
    # _collect() never walks data/rag/ (not a listed source), so exercise _excluded()
    # directly against the path shape the plan calls out.
    p = fake_repo / "data" / "rag" / "index_fixed.json"
    assert bpc._excluded(p) is True


def test_includes_expected_sources(fake_repo):
    files = bpc._collect()
    rels = {f.relative_to(fake_repo).as_posix() for f in files}

    assert "README.md" in rels
    assert "CLAUDE.md" in rels
    assert "memory-bank/progress.md" in rels
    assert "memory-bank/lessons/week-05-rag.md" in rels
    assert "week-05/day-22/README.md" in rels
    assert "agent-web/agent_web/app.py" in rels


def test_header_parsed_by_existing_parse_header(fake_repo):
    text = "<!-- source: README.md | title: README.md -->\n\n# Hello\n"
    source, title = bpc.parse_header(text)
    assert source == "README.md"
    assert title == "README.md"


def test_header_missing_defaults_unknown():
    source, title = bpc.parse_header("no header here")
    assert source == ""
    assert title == "Unknown"
