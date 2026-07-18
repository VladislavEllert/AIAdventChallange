"""Day 35: rituals/day_report.py — collector/writer/verifier chain.

collect() is tested against a temp git repo (hermetic — not the real repo).
draft() is tested with an injected chat_fn (no live LLM call). verify()
covers the plan's explicit acceptance cases: broken table, missing link,
hallucinated video claim."""
import subprocess

import pytest

from agent_web.services.rituals import day_report


def _run(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def repo(tmp_path):
    _run(["init"], cwd=tmp_path)
    _run(["config", "user.email", "test@test.local"], cwd=tmp_path)
    _run(["config", "user.name", "Test"], cwd=tmp_path)
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    _run(["add", "a.txt"], cwd=tmp_path)
    _run(["commit", "-m", "initial"], cwd=tmp_path)
    return tmp_path


# ── collect() ────────────────────────────────────────────────────────────
def test_collect_reads_real_diff_from_temp_repo(repo):
    (repo / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    (repo / "new_file.py").write_text("print(1)\n", encoding="utf-8")

    collected = day_report.collect(repo, "07", "99", metrics_path=repo / "no_such_metrics.jsonl")

    assert "world" in collected.diff
    assert any("new_file.py" in f for f in collected.changed_files)
    assert collected.week == "07"
    assert collected.day == "99"


def test_collect_clean_repo_has_no_changed_files(repo):
    collected = day_report.collect(repo, "07", "99", metrics_path=repo / "no_such_metrics.jsonl")
    assert collected.changed_files == []
    assert collected.diff == ""


def test_collect_survives_missing_metrics_file(repo):
    collected = day_report.collect(repo, "07", "99", metrics_path=repo / "does_not_exist.jsonl")
    assert "no review metrics" in collected.metrics_summary


# ── draft() ──────────────────────────────────────────────────────────────
def test_draft_calls_chat_fn_with_forced_model_and_returns_stripped_text():
    collected = day_report.Collected(week="07", day="99", diff="", changed_files=[], metrics_summary="")
    calls = []

    def fake_chat_fn(messages, model):
        calls.append((messages, model))
        return "  | 07 | 99 | test | done | [x](y) | todo |  \n"

    row = day_report.draft(collected, chat_fn=fake_chat_fn, model=day_report.MODEL)

    assert row == "| 07 | 99 | test | done | [x](y) | todo |"
    assert calls[0][1] == day_report.MODEL
    assert calls[0][0][0]["role"] == "system"
    assert "invent" in calls[0][0][0]["content"].lower() or "hallucinat" in calls[0][0][0]["content"].lower()


def test_draft_strips_header_and_separator_if_model_echoes_them():
    """Regression: caught live during the day-35 dry run — the model
    sometimes echoes the table header + '|---|' separator before the real
    data row despite being told not to. draft() must recover the actual row."""
    collected = day_report.Collected(week="07", day="99", diff="", changed_files=[], metrics_summary="")

    def chatty_fn(messages, model):
        return (
            "| Неделя | День | Задача | Статус | Код | Видео |\n"
            "|--------|------|--------|--------|-----|-------|\n"
            "| 07     | 99   | test   | done   | [week-07/day-99](week-07/day-99/) | todo |\n"
        )

    row = day_report.draft(collected, chat_fn=chatty_fn, model=day_report.MODEL)
    assert row.startswith("| 07")
    assert "Неделя" not in row
    assert "---" not in row
    vr = day_report.verify(row, collected)
    assert vr.ok, vr.errors


# ── verify() ─────────────────────────────────────────────────────────────
def _collected():
    return day_report.Collected(week="07", day="99", diff="", changed_files=[], metrics_summary="")


def test_verify_accepts_well_formed_row():
    row = "| 07 | 99 | test task | done | [week-07/day-99](week-07/day-99/) | todo |"
    vr = day_report.verify(row, _collected())
    assert vr.ok
    assert vr.errors == []


def test_verify_rejects_broken_table_wrong_column_count():
    row = "| 07 | 99 | only three cols |"
    vr = day_report.verify(row, _collected())
    assert not vr.ok
    assert any("column" in e for e in vr.errors)


def test_verify_rejects_row_not_wrapped_in_pipes():
    row = "07 | 99 | test | done | [x](y) | todo"
    vr = day_report.verify(row, _collected())
    assert not vr.ok


def test_verify_rejects_missing_link_in_code_column():
    row = "| 07 | 99 | test task | done | week-07/day-99 no link | todo |"
    vr = day_report.verify(row, _collected())
    assert not vr.ok
    assert any("link" in e for e in vr.errors)


def test_verify_rejects_hallucinated_video_link():
    """Explicit plan acceptance case: draft claims a video link exists when
    none was recorded — collect() never gathers video evidence, so ANY
    non-'todo' Видео claim must be rejected."""
    row = "| 07 | 99 | test task | done | [x](y) | https://www.loom.com/share/fakefakefake |"
    vr = day_report.verify(row, _collected())
    assert not vr.ok
    assert any("hallucinat" in e.lower() or "video" in e.lower() or "видео" in e.lower() for e in vr.errors)


def test_verify_rejects_bad_status_value():
    row = "| 07 | 99 | test task | in-progress | [x](y) | todo |"
    vr = day_report.verify(row, _collected())
    assert not vr.ok
    assert any("Статус" in e for e in vr.errors)


# ── build_patch() ────────────────────────────────────────────────────────
_HEADER = "| Неделя | День | Задача | Статус | Код | Видео |\n|--------|------|--------|--------|-----|-------|\n"


def test_build_patch_inserts_new_day_row(tmp_path):
    (tmp_path / "README.md").write_text(
        _HEADER + "| 07 | 31 | foo | done | [x](x) | todo |\n", encoding="utf-8",
    )
    (tmp_path / "memory-bank").mkdir()
    (tmp_path / "memory-bank" / "progress.md").write_text(
        _HEADER + "| 07 | 31 | foo | done | [x](x) | todo |\n", encoding="utf-8",
    )

    new_row = "| 07 | 35 | ritual | done | [week-07/day-35](week-07/day-35/) | todo |"
    patch = day_report.build_patch(tmp_path, "35", new_row)

    assert new_row in patch.files["README.md"]
    assert new_row in patch.files["memory-bank/progress.md"]
    assert "| 07 | 31 | foo" in patch.files["README.md"]  # existing row untouched
    assert patch.diff_text  # non-empty diff shown


def test_build_patch_replaces_existing_day_row_not_duplicates(tmp_path):
    (tmp_path / "README.md").write_text(
        _HEADER + "| 07 | 35 | old draft | todo | [x](x) | todo |\n", encoding="utf-8",
    )
    (tmp_path / "memory-bank").mkdir()
    (tmp_path / "memory-bank" / "progress.md").write_text(
        _HEADER + "| 07 | 35 | old draft | todo | [x](x) | todo |\n", encoding="utf-8",
    )

    new_row = "| 07 | 35 | new draft | done | [week-07/day-35](week-07/day-35/) | todo |"
    patch = day_report.build_patch(tmp_path, "35", new_row)

    readme = patch.files["README.md"]
    assert readme.count("| 07 | 35 |") == 1
    assert "new draft" in readme
    assert "old draft" not in readme


# ── run_ritual() end-to-end (no LLM, injected chat_fn) ─────────────────────
def test_run_ritual_rejected_draft_has_no_patch(repo):
    (repo / "memory-bank").mkdir()
    (repo / "memory-bank" / "progress.md").write_text(_HEADER, encoding="utf-8")
    (repo / "README.md").write_text(_HEADER, encoding="utf-8")

    def bad_chat_fn(messages, model):
        return "not a table row at all"

    result = day_report.run_ritual(repo, "07", "99", chat_fn=bad_chat_fn)
    assert not result.verify_result.ok
    assert result.patch is None


def test_run_ritual_approved_draft_has_patch(repo):
    (repo / "memory-bank").mkdir()
    (repo / "memory-bank" / "progress.md").write_text(_HEADER, encoding="utf-8")
    (repo / "README.md").write_text(_HEADER, encoding="utf-8")

    def good_chat_fn(messages, model):
        return "| 07 | 99 | test | done | [week-07/day-99](week-07/day-99/) | todo |"

    result = day_report.run_ritual(repo, "07", "99", chat_fn=good_chat_fn)
    assert result.verify_result.ok
    assert result.patch is not None
    assert "| 07 | 99 |" in result.patch.files["README.md"]
