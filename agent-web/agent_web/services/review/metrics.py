"""Day 32.3: review run metrics -> data/review_metrics.jsonl.

One JSON line per review run: ts, pr, model, prompt_version, latency_ms,
tokens, cost_rub, ok, retries, human_score. `human_score` starts as None and
is filled in later by `python -m agent_web.services.review score <run_id> <1-5>`
(see __main__.py) — that's the quality-gate input the lecture's rubric wants.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

METRICS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "review_metrics.jsonl"


@dataclass
class ReviewMetric:
    ts: float
    run_id: str
    pr: str | int | None
    model: str
    prompt_version: str
    latency_ms: float
    tokens: int
    cost_rub: float
    ok: bool
    retries: int
    human_score: int | None = None


def record(metric: ReviewMetric, path: Path | None = None) -> None:
    # `path` resolves against the module-level METRICS_PATH at CALL time, not
    # at def time — a plain `path: Path = METRICS_PATH` default is bound once
    # at import, so tests monkeypatching `metrics.METRICS_PATH` would be
    # silently ignored and every write would land on the real data file.
    path = path or METRICS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")


def read_all(path: Path | None = None) -> list[dict]:
    path = path or METRICS_PATH
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def set_human_score(run_id: str, score: int, path: Path | None = None) -> bool:
    """Write `score` onto every record matching `run_id` (normally exactly
    one). Returns False if `run_id` isn't found — caller should treat that
    as an error, not a silent no-op."""
    path = path or METRICS_PATH
    records = read_all(path)
    found = False
    for r in records:
        if r.get("run_id") == run_id:
            r["human_score"] = score
            found = True
    if found:
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return found


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


@dataclass
class Aggregate:
    count: int
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_cost_rub: float
    pct_successful: float
    quality_gate: float | None  # avg human_score over the last N *scored* runs; None if none scored


def aggregate(records: list[dict], quality_gate_n: int = 20) -> Aggregate:
    if not records:
        return Aggregate(0, 0.0, 0.0, 0.0, 0.0, 0.0, None)

    latencies = [r["latency_ms"] for r in records]
    costs = [r["cost_rub"] for r in records]
    n_ok = sum(1 for r in records if r.get("ok"))

    scored = [r for r in records if r.get("human_score") is not None]
    scored_recent = sorted(scored, key=lambda r: r["ts"])[-quality_gate_n:]
    quality_gate = (
        sum(r["human_score"] for r in scored_recent) / len(scored_recent) if scored_recent else None
    )

    return Aggregate(
        count=len(records),
        p50_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        p99_latency_ms=_percentile(latencies, 0.99),
        avg_cost_rub=sum(costs) / len(costs) if costs else 0.0,
        pct_successful=100.0 * n_ok / len(records),
        quality_gate=quality_gate,
    )
