"""Day 32: diff parser — extract files + line numbers from the 4 review_eval
fixtures without any LLM call (plan's Tests table: "diff parser")."""
from pathlib import Path

from agent_web.services.review.pipeline import build_rag_queries, parse_diff

FIXTURES_DIR = Path(__file__).parent.parent / "review_eval" / "fixtures"


def _fixture_names() -> list[str]:
    return sorted(p.stem for p in FIXTURES_DIR.glob("*.diff"))


def test_fixtures_exist():
    names = _fixture_names()
    assert len(names) == 4


def test_parse_diff_extracts_files_and_line_numbers_for_all_fixtures():
    for name in _fixture_names():
        diff_text = (FIXTURES_DIR / f"{name}.diff").read_text(encoding="utf-8")
        files = parse_diff(diff_text)
        assert len(files) >= 1, f"{name}: expected at least one changed file"
        for f in files:
            assert f.path, f"{name}: file diff has empty path"
            assert len(f.hunks) >= 1, f"{name}: {f.path} has no hunks"
            line_numbers = f.added_line_numbers()
            assert line_numbers, f"{name}: {f.path} has no added lines"
            assert all(isinstance(ln, int) and ln > 0 for ln in line_numbers)


def test_parse_diff_new_file_fixture():
    diff_text = (FIXTURES_DIR / "01_dotenv_wrong_env.diff").read_text(encoding="utf-8")
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0].path == "agent-cli/agent_cli/quickstart.py"
    # First added line ("""One-off script...) sits at new-file line 1.
    assert files[0].hunks[0].new_start == 1
    assert files[0].hunks[0].added_lines[0][0] == 1


def test_parse_diff_modified_file_fixture_line_numbers():
    diff_text = (FIXTURES_DIR / "02_isinstance_breaks_streaming.diff").read_text(encoding="utf-8")
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0].path == "agent-web/agent_web/services/agent_manager.py"
    assert len(files[0].hunks) == 2
    # Second hunk header says "+89,17" -> new_start == 89
    assert files[0].hunks[1].new_start == 89


def test_parse_diff_no_llm_call_needed():
    """Parsing is pure — no network/provider dependency at all."""
    diff_text = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,1 +1,2 @@\n+new line\n old\n"
    files = parse_diff(diff_text)
    assert files[0].path == "x.py"
    assert files[0].added_line_numbers() == [1]


def test_build_rag_queries_includes_paths_and_symbols():
    diff_text = (FIXTURES_DIR / "01_dotenv_wrong_env.diff").read_text(encoding="utf-8")
    files = parse_diff(diff_text)
    queries = build_rag_queries(files)
    assert "agent-cli/agent_cli/quickstart.py" in queries
    assert any("load_config" in q for q in queries)


def test_build_rag_queries_capped():
    diff_text = "\n".join(
        f"diff --git a/f{i}.py b/f{i}.py\n--- a/f{i}.py\n+++ b/f{i}.py\n@@ -1,1 +1,1 @@\n+x = {i}"
        for i in range(10)
    )
    files = parse_diff(diff_text)
    queries = build_rag_queries(files, cap=5)
    assert len(queries) == 5
