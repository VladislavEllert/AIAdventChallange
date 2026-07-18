"""Day 32: review CLI — mocked provider, zero live ProxyAPI calls.

Covers: three-section parsing end to end through cmd_review, nonzero exit on
an empty LLM response, and the "no API key" degradation path (32.8):
a provider that always raises must degrade to the deterministic-failure
message and a nonzero exit — never a crash.
"""
import argparse
from pathlib import Path

import pytest

from agent_web.services.review import __main__ as review_cli
from agent_web.services.review import metrics as metrics_mod
from agent_cli.llm.provider import TokenUsage

GOOD_REVIEW_TEXT = (
    "## Potential bugs\n"
    "- `foo.py:10` uses a bare except\n\n"
    "## Architectural issues\n"
    "- none found\n\n"
    "## Recommendations\n"
    "- add a type hint to `bar()`\n"
)

DIFF_TEXT = (
    "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n"
    "@@ -1,1 +1,2 @@\n+def bar():\n     pass\n"
)


class _StubProvider:
    """Minimal stand-in for DispatchProvider — no network."""

    def __init__(self, response: str, raises: bool = False):
        self.response = response
        self.raises = raises
        self.calls = 0

    def chat_with_stats(self, messages, model, **kwargs):
        self.calls += 1
        if self.raises:
            raise RuntimeError("simulated: no/invalid API key")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150,
                            elapsed_ms=10.0, cost_rub=0.005)
        return self.response, usage


def _base_args(**overrides) -> argparse.Namespace:
    defaults = dict(
        diff_file=None, pr=None, base=None, head=None, repo_root=".",
        model="openai/gpt-4o-mini", dry_run=True, post_comment=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture(autouse=True)
def _no_rag(monkeypatch):
    # kb resolution isn't the point of this test file; force "no RAG context"
    # so cmd_review doesn't need a real index.
    monkeypatch.setattr(review_cli, "_get_project_rag", lambda: (None, None, "proxyapi"))


@pytest.fixture(autouse=True)
def _isolated_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(metrics_mod, "METRICS_PATH", tmp_path / "review_metrics.jsonl")


def test_cmd_review_parses_three_sections(tmp_path, capsys):
    diff_path = tmp_path / "pr.diff"
    diff_path.write_text(DIFF_TEXT, encoding="utf-8")
    provider = _StubProvider(GOOD_REVIEW_TEXT)

    args = _base_args(diff_file=str(diff_path))
    rc = review_cli.cmd_review(args, provider=provider)

    assert rc == 0
    out = capsys.readouterr().out
    assert "## Potential bugs" in out
    assert "bare except" in out
    assert "## Architectural issues" in out
    assert "## Recommendations" in out
    assert "add a type hint" in out
    assert provider.calls == 1


def test_cmd_review_nonzero_exit_on_empty_response(tmp_path, capsys):
    diff_path = tmp_path / "pr.diff"
    diff_path.write_text(DIFF_TEXT, encoding="utf-8")
    provider = _StubProvider("")  # empty LLM response

    args = _base_args(diff_file=str(diff_path))
    rc = review_cli.cmd_review(args, provider=provider)

    assert rc == 1
    err = capsys.readouterr().err
    assert review_cli.DETERMINISTIC_FAILURE_MSG in err


def test_cmd_review_degrades_on_provider_failure_no_api_key(tmp_path, capsys):
    """32.8: simulates a missing/invalid PROXYAPI_KEY — provider.chat_with_stats
    raises on every call. Must degrade to the deterministic-failure message and
    exit 1, never crash."""
    diff_path = tmp_path / "pr.diff"
    diff_path.write_text(DIFF_TEXT, encoding="utf-8")
    provider = _StubProvider("irrelevant", raises=True)

    # Distinct from FALLBACK_MODEL so the ladder actually has 3 rungs
    # (primary x2 + fallback x1) instead of collapsing to 2 identical ones.
    args = _base_args(diff_file=str(diff_path), model="ollama/qwen3:4b")
    rc = review_cli.cmd_review(args, provider=provider)

    assert rc == 1
    err = capsys.readouterr().err
    assert review_cli.DETERMINISTIC_FAILURE_MSG in err
    # ladder tried primary x2 (1 retry) + fallback x1 = 3 attempts, all failed
    assert provider.calls == 3


def test_cmd_review_records_metrics_unless_dry_run(tmp_path):
    diff_path = tmp_path / "pr.diff"
    diff_path.write_text(DIFF_TEXT, encoding="utf-8")
    provider = _StubProvider(GOOD_REVIEW_TEXT)

    args = _base_args(diff_file=str(diff_path), dry_run=False)
    review_cli.cmd_review(args, provider=provider)

    records = metrics_mod.read_all()
    assert len(records) == 1
    assert records[0]["ok"] is True
    assert records[0]["tokens"] == 150


def test_score_subcommand_writes_human_score(tmp_path):
    metrics_mod.record(metrics_mod.ReviewMetric(
        ts=1.0, run_id="run-abc", pr=None, model="m", prompt_version="v1",
        latency_ms=1.0, tokens=1, cost_rub=0.0, ok=True, retries=0,
    ))
    args = argparse.Namespace(run_id="run-abc", score=4)
    rc = review_cli.cmd_score(args)
    assert rc == 0
    records = metrics_mod.read_all()
    assert records[0]["human_score"] == 4


def test_score_subcommand_unknown_run_id_nonzero_exit(capsys):
    args = argparse.Namespace(run_id="nope", score=3)
    rc = review_cli.cmd_score(args)
    assert rc == 1


def test_build_parser_diff_file_mode():
    parser = review_cli.build_parser()
    args = parser.parse_args(["--diff-file", "x.diff", "--model", "m", "--dry-run"])
    assert args.diff_file == "x.diff"
    assert args.model == "m"
    assert args.dry_run is True
    assert args.func is review_cli.cmd_review


def test_build_parser_score_subcommand():
    parser = review_cli.build_parser()
    args = parser.parse_args(["score", "run-1", "5"])
    assert args.run_id == "run-1"
    assert args.score == 5
    assert args.func is review_cli.cmd_score
