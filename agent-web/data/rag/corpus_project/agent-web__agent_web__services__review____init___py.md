<!-- source: agent-web/agent_web/services/review/__init__.py | title: __init__.py -->

"""Day 32: headless AI PR review — diff-in, three-section review-out.

Submodules:
- pipeline: pure diff -> ReviewResult. Parses unified diff, pulls RAG context
  by filename/symbol, builds the prompt, parses the LLM reply into three
  sections. No GitHub API calls happen here.
- resilience: timeout -> retry -> fallback model -> deterministic failure.
  Wraps a single provider call; never raises past its own boundary.
- metrics: appends runs to data/review_metrics.jsonl, aggregates
  p50/p95/p99 latency, cost/run, % successful, quality gate.
- __main__: CLI (`python -m agent_web.services.review`).

`review_eval/` (sibling of `agent_web/`, not under this package) holds the 4
fixture diffs + the live eval harness — see review_eval/run_eval.py.
"""
