"""Day 31: dependencies.get_rag_index — per-KB cache, unknown kb, dim mismatch."""
import json

import pytest

import agent_web.dependencies as deps
from agent_web.services.rag.index import Chunk


def _fake_index_file(tmp_path, dim: int, n: int = 2):
    chunks = [
        Chunk(
            chunk_id=f"c{i}", text=f"text {i}", embedding=[0.1] * dim,
            source=f"src{i}", title="t", section="s", strategy="fixed",
        )
        for i in range(n)
    ]
    path = tmp_path / "idx.json"
    path.write_text(json.dumps([c.__dict__ for c in chunks], ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_cache():
    deps._rag_indexes.clear()
    yield
    deps._rag_indexes.clear()


def test_unknown_kb_raises(monkeypatch):
    with pytest.raises(ValueError, match="Unknown knowledge base"):
        deps.get_rag_index(kb="does-not-exist")


def test_handbook_and_project_cached_separately(tmp_path, monkeypatch):
    hb_path = _fake_index_file(tmp_path, dim=768)
    (tmp_path / "p").mkdir(exist_ok=True)
    proj_path = _fake_index_file(tmp_path / "p", dim=512)

    fake_kb = {
        "handbook": {"index_path": hb_path, "dim": 768, "label": "H"},
        "project": {"index_path": proj_path, "dim": 512, "label": "P"},
    }
    monkeypatch.setattr(deps, "KNOWLEDGE_BASES", fake_kb)

    hb_index = deps.get_rag_index(kb="handbook")
    proj_index = deps.get_rag_index(kb="project")

    assert hb_index is not proj_index
    assert len(hb_index[0].embedding) == 768
    assert len(proj_index[0].embedding) == 512

    # cache hit — same object on second call, no re-read
    assert deps.get_rag_index(kb="handbook") is hb_index


def test_index_swapped_by_fixture_reflected_on_next_uncached_load(tmp_path, monkeypatch):
    path_a = _fake_index_file(tmp_path, dim=8, n=1)
    fake_kb = {"handbook": {"index_path": path_a, "dim": 8, "label": "H"}}
    monkeypatch.setattr(deps, "KNOWLEDGE_BASES", fake_kb)

    idx1 = deps.get_rag_index(kb="handbook")
    assert idx1[0].source == "src0"

    # swap underlying file + clear cache — simulates a rebuilt index
    (tmp_path / "b2").mkdir(exist_ok=True)
    path_b = _fake_index_file(tmp_path / "b2", dim=8, n=1)
    fake_kb["handbook"]["index_path"] = path_b
    deps._rag_indexes.clear()

    idx2 = deps.get_rag_index(kb="handbook")
    assert idx2[0].source == "src0"  # same content shape, but loaded from the new path
    assert idx2 is not idx1


def test_dim_mismatch_fails_loudly(tmp_path, monkeypatch):
    path = _fake_index_file(tmp_path, dim=512)
    fake_kb = {"handbook": {"index_path": path, "dim": 768, "label": "H"}}
    monkeypatch.setattr(deps, "KNOWLEDGE_BASES", fake_kb)

    with pytest.raises(ValueError, match="768d"):
        deps.get_rag_index(kb="handbook")
