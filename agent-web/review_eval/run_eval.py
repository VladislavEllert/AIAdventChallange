"""Day 32.6: review eval harness — LIVE tool, not part of `pytest`.

Runs real ProxyAPI calls (via DispatchProvider / DEFAULT_MODEL) against the
4 fixtures in review_eval/fixtures/, computes recall (buggy fixtures
correctly flagged) + false-positive rate (clean fixture wrongly flagged) +
latency p50/p95/p99 + cost/run + % successful, and writes
review_eval/results_day32.md.

This is deliberately NOT a pytest test: the recall metric only means
something against a real model, and the "zero live calls in the default
pytest run" rule (see plan's Tests section) would make a pytest version of
this either fake (mocked, meaningless for recall) or a rule violation. The
pytest suite (tests/test_review_*.py) covers this module's plumbing
(diff parsing, resilience ladder, metrics aggregation, CLI three-section
parsing) with mocks; this script is the live counterpart, run manually:

    cd agent-web
    .venv/bin/python3 review_eval/run_eval.py
    .venv/bin/python3 review_eval/run_eval.py --prompt-version v2_strict --label "day 35 comparison"

Needs PROXYAPI_KEY — loaded from repo-root .env the same way rag_eval's
run_eval.py does. Every run APPENDS a new "## Прогон N" section to
results_day32.md (day 35.6) — prior baselines are never overwritten.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).parent.parent.parent / ".env"
if _ROOT_ENV.exists():
    load_dotenv(_ROOT_ENV)

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_cli.config import DEFAULT_MODEL  # noqa: E402
from agent_cli.llm.dispatch import DispatchProvider  # noqa: E402
from agent_web.services.rag.config import INDEX_PROJECT_PROXY, KNOWLEDGE_BASES  # noqa: E402
from agent_web.services.rag.index import load_index  # noqa: E402
from agent_web.services.review import metrics as metrics_mod  # noqa: E402
from agent_web.services.review.pipeline import (  # noqa: E402
    PROMPT_VERSION, PROMPT_VERSION_V2, run_review,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESULTS_PATH = Path(__file__).parent / "results_day32.md"


def _index_content_hash() -> str:
    """sha256[:12] of the project RAG index used for this eval run. Day 33
    rebuilds the corpus — record this so a silently-rotted baseline (index
    changed, numbers didn't move because nobody re-ran the eval) is
    detectable instead of assumed-still-valid."""
    if not INDEX_PROJECT_PROXY.exists():
        return "N/A (index_project_proxy.json missing)"
    return hashlib.sha256(INDEX_PROJECT_PROXY.read_bytes()).hexdigest()[:12]


def _changed_files_from_diff(diff_text: str) -> list[str]:
    return sorted({
        line.split(" b/", 1)[-1]
        for line in diff_text.splitlines()
        if line.startswith("diff --git ")
    })


def load_fixtures() -> list[tuple[str, str, dict]]:
    fixtures = []
    for diff_path in sorted(FIXTURES_DIR.glob("*.diff")):
        expected_path = FIXTURES_DIR / (diff_path.stem + ".expected.json")
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        fixtures.append((diff_path.stem, diff_path.read_text(encoding="utf-8"), expected))
    return fixtures


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def run_one(
    name: str, diff_text: str, expected: dict, provider, index, backend: str,
    prompt_version: str = PROMPT_VERSION,
) -> dict:
    changed_files = _changed_files_from_diff(diff_text)
    usage_box: dict = {}

    def _chat_fn(messages: list[dict], model: str) -> str:
        text, usage = provider.chat_with_stats(messages, model, max_tokens=1500, temperature=0.2)
        usage_box["usage"] = usage
        return text

    t0 = time.time()
    ok = True
    error = None
    result = None
    try:
        result = run_review(
            diff_text, changed_files, "project", DEFAULT_MODEL,
            chat_fn=_chat_fn, index=index, backend=backend, prompt_version=prompt_version,
        )
        ok = result.ok
    except Exception as e:  # eval harness itself must not crash on one bad fixture
        ok = False
        error = str(e)
    latency_ms = (time.time() - t0) * 1000
    usage = usage_box.get("usage")

    findings_text = ""
    if result:
        findings_text = " ".join(result.bugs + result.architecture + result.recommendations)

    must_mention = expected.get("must_mention") or []
    if must_mention:
        flagged = any(kw.lower() in findings_text.lower() for kw in must_mention)
    else:
        flagged = bool(result and (result.bugs or result.architecture))

    return {
        "name": name, "ok": ok, "error": error, "latency_ms": latency_ms,
        "usage": usage, "flagged": flagged, "expect_flag": expected["expect_flag"],
        "result": result,
    }


def _next_run_number() -> int:
    if not RESULTS_PATH.exists():
        return 1
    text = RESULTS_PATH.read_text(encoding="utf-8")
    existing = re.findall(r"^## Прогон (\d+)", text, flags=re.M)
    return (max(int(n) for n in existing) + 1) if existing else 1


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt-version", default=PROMPT_VERSION, choices=[PROMPT_VERSION, PROMPT_VERSION_V2],
        help=f"Which system prompt to eval (default {PROMPT_VERSION!r})",
    )
    parser.add_argument(
        "--label", default="", help="Free-text label for this run's section header (e.g. why it was run)",
    )
    args = parser.parse_args(argv)

    fixtures = load_fixtures()
    provider = DispatchProvider()

    index = None
    backend = "proxyapi"
    try:
        cfg = KNOWLEDGE_BASES["project"]
        index = load_index(cfg["index_path"], dim=cfg["dim"])
        backend = cfg["backend"]
    except Exception as e:
        print(f"warning: RAG context unavailable ({e})", file=sys.stderr)

    rows = []
    for name, diff_text, expected in fixtures:
        print(f"running {name}...")
        row = run_one(name, diff_text, expected, provider, index, backend, prompt_version=args.prompt_version)
        rows.append(row)
        status = "OK" if row["ok"] else "FAIL"
        print(
            f"  {status} flagged={row['flagged']} expect_flag={row['expect_flag']} "
            f"latency={row['latency_ms']:.0f}ms"
        )
        metrics_mod.record(metrics_mod.ReviewMetric(
            ts=time.time(), run_id=f"eval-{name}-{args.prompt_version}", pr=None, model=DEFAULT_MODEL,
            prompt_version=args.prompt_version, latency_ms=row["latency_ms"],
            tokens=(row["usage"].total_tokens if row["usage"] else 0),
            cost_rub=(row["usage"].cost_rub if row["usage"] else 0.0),
            ok=row["ok"], retries=0, human_score=None,
        ))

    buggy = [r for r in rows if r["expect_flag"]]
    clean = [r for r in rows if not r["expect_flag"]]
    recall = sum(1 for r in buggy if r["flagged"]) / len(buggy) if buggy else 0.0
    fp_rate = sum(1 for r in clean if r["flagged"]) / len(clean) if clean else 0.0

    latencies = [r["latency_ms"] for r in rows]
    costs = [r["usage"].cost_rub for r in rows if r["usage"]]
    n_ok = sum(1 for r in rows if r["ok"])

    p50, p95, p99 = _percentile(latencies, 0.5), _percentile(latencies, 0.95), _percentile(latencies, 0.99)
    avg_cost = sum(costs) / len(costs) if costs else 0.0
    pct_successful = 100.0 * n_ok / len(rows) if rows else 0.0

    print(f"\nRecall (баги найдены / всего багов): {recall:.0%} "
          f"({sum(1 for r in buggy if r['flagged'])}/{len(buggy)})")
    print(f"False positive rate: {fp_rate:.0%} ({sum(1 for r in clean if r['flagged'])}/{len(clean)})")
    print(f"Latency p50 / p95 / p99: {p50:.0f}ms / {p95:.0f}ms / {p99:.0f}ms")
    print(f"Cost за прогон (среднее): {avg_cost:.4f}₽")
    print(f"% успешных прогонов: {pct_successful:.0f}%")

    index_hash = _index_content_hash()
    run_no = _next_run_number()
    label_suffix = f" — {args.label}" if args.label else ""
    lines = [
        f"\n---\n\n## Прогон {run_no} (prompt_version=`{args.prompt_version}`{label_suffix})\n\n",
        f"Прогон: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"Модель: `{DEFAULT_MODEL}`, prompt_version: `{args.prompt_version}`\n\n",
        f"RAG-индекс `index_project_proxy.json` content-hash (sha256[:12]): `{index_hash}` "
        "— день 33 пересобирает корпус; если этот хэш изменился, а числа ниже не пересчитаны, "
        "baseline устарел.\n\n",
        "### Метрики\n\n",
        f"- Recall (баги найдены / всего багов): **{recall:.0%}** "
        f"({sum(1 for r in buggy if r['flagged'])}/{len(buggy)})\n",
        f"- False positive rate (чистая фикстура ошибочно помечена): **{fp_rate:.0%}** "
        f"({sum(1 for r in clean if r['flagged'])}/{len(clean)})\n",
        f"- Latency p50 / p95 / p99: {p50:.0f}ms / {p95:.0f}ms / {p99:.0f}ms\n",
        f"- Cost за прогон (среднее): {avg_cost:.4f}₽\n",
        f"- % успешных прогонов: {pct_successful:.0f}%\n\n",
        "### Детали по фикстурам\n\n",
        "| fixture | bug_class | expect_flag | flagged | ok | latency_ms |\n",
        "|---|---|---|---|---|---|\n",
    ]
    for (name, _, expected), r in zip(fixtures, rows):
        lines.append(
            f"| {name} | {expected.get('bug_class', '')} | {r['expect_flag']} | "
            f"{r['flagged']} | {r['ok']} | {r['latency_ms']:.0f} |\n"
        )

    # APPEND, never overwrite (day 35.6: baselines from prior runs/prompt
    # versions must stay visible for comparison) — day 32's original run
    # pre-dates this append logic and was written by a full-file write_text();
    # every run since (including this one) only ever adds a new section.
    if not RESULTS_PATH.exists():
        header = "# День 32 — AI-ревью PR: eval-результаты\n"
        RESULTS_PATH.write_text(header + "".join(lines), encoding="utf-8")
    else:
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write("".join(lines))
    print(f"\nappended run {run_no} to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
