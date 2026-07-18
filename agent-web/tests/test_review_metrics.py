"""Day 32: metrics — jsonl record/read/set_human_score + aggregate
(p50/p95/p99, cost, % successful, quality gate). Synthetic 20-record jsonl,
no LLM/network."""
import json

from agent_web.services.review.metrics import (
    ReviewMetric,
    _percentile,
    aggregate,
    read_all,
    record,
    set_human_score,
)


def _make_records(n: int = 20) -> list[dict]:
    records = []
    for i in range(n):
        records.append({
            "ts": 1000.0 + i,
            "run_id": f"run-{i}",
            "pr": i,
            "model": "openai/gpt-4o-mini",
            "prompt_version": "v1",
            "latency_ms": float(100 + i * 10),  # 100..290
            "tokens": 500 + i,
            "cost_rub": 0.01 + i * 0.001,
            "ok": i % 5 != 0,  # 16/20 ok (80%)
            "retries": i % 3,
            "human_score": (i % 5) + 1 if i % 2 == 0 else None,  # 10 scored
        })
    return records


def test_record_and_read_roundtrip(tmp_path):
    path = tmp_path / "metrics.jsonl"
    m = ReviewMetric(
        ts=1.0, run_id="abc", pr=None, model="m", prompt_version="v1",
        latency_ms=10.0, tokens=5, cost_rub=0.01, ok=True, retries=0,
    )
    record(m, path=path)
    records = read_all(path)
    assert len(records) == 1
    assert records[0]["run_id"] == "abc"
    assert records[0]["human_score"] is None


def test_read_all_missing_file_returns_empty(tmp_path):
    assert read_all(tmp_path / "does_not_exist.jsonl") == []


def test_set_human_score_writes_and_returns_true(tmp_path):
    path = tmp_path / "metrics.jsonl"
    record(ReviewMetric(ts=1.0, run_id="r1", pr=None, model="m", prompt_version="v1",
                         latency_ms=1.0, tokens=1, cost_rub=0.0, ok=True, retries=0), path=path)
    ok = set_human_score("r1", 4, path=path)
    assert ok is True
    records = read_all(path)
    assert records[0]["human_score"] == 4


def test_set_human_score_unknown_run_id_returns_false(tmp_path):
    path = tmp_path / "metrics.jsonl"
    record(ReviewMetric(ts=1.0, run_id="r1", pr=None, model="m", prompt_version="v1",
                         latency_ms=1.0, tokens=1, cost_rub=0.0, ok=True, retries=0), path=path)
    ok = set_human_score("does-not-exist", 3, path=path)
    assert ok is False
    # file must be untouched — no partial/garbage rewrite on a miss
    assert json.loads(path.read_text().strip())["human_score"] is None


def test_aggregate_empty_records():
    agg = aggregate([])
    assert agg.count == 0
    assert agg.quality_gate is None
    assert agg.pct_successful == 0.0


def test_aggregate_synthetic_20_records_percentiles_and_pct_successful():
    records = _make_records(20)
    agg = aggregate(records)

    assert agg.count == 20
    assert agg.pct_successful == 80.0  # 16/20 ok

    latencies = [r["latency_ms"] for r in records]
    assert agg.p50_latency_ms == _percentile(latencies, 0.50)
    assert agg.p95_latency_ms == _percentile(latencies, 0.95)
    assert agg.p99_latency_ms == _percentile(latencies, 0.99)
    assert agg.p50_latency_ms <= agg.p95_latency_ms <= agg.p99_latency_ms

    expected_avg_cost = sum(r["cost_rub"] for r in records) / len(records)
    assert abs(agg.avg_cost_rub - expected_avg_cost) < 1e-9


def test_aggregate_quality_gate_over_last_n_scored():
    records = _make_records(20)
    scored = [r for r in records if r["human_score"] is not None]
    assert len(scored) == 10

    agg_all = aggregate(records, quality_gate_n=100)
    expected_all = sum(r["human_score"] for r in scored) / len(scored)
    assert abs(agg_all.quality_gate - expected_all) < 1e-9

    agg_recent = aggregate(records, quality_gate_n=3)
    recent_3 = sorted(scored, key=lambda r: r["ts"])[-3:]
    expected_recent = sum(r["human_score"] for r in recent_3) / 3
    assert abs(agg_recent.quality_gate - expected_recent) < 1e-9


def test_aggregate_no_scored_runs_quality_gate_none():
    records = [
        {"ts": 1.0, "latency_ms": 10.0, "cost_rub": 0.01, "ok": True, "human_score": None}
    ]
    agg = aggregate(records)
    assert agg.quality_gate is None
