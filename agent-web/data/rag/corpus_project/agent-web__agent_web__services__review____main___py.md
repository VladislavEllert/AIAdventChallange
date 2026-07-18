<!-- source: agent-web/agent_web/services/review/__main__.py | title: __main__.py -->

"""Day 32.4: headless AI PR review CLI.

    python -m agent_web.services.review --diff-file <path> [--model M] [--dry-run] [--post-comment]
    python -m agent_web.services.review --base <sha> --head <sha> [--repo-root <path>] ...
    python -m agent_web.services.review score <run_id> <1-5>

No GitHub API call happens unless --post-comment is passed, and even then it
degrades to a warning (not a crash) if GITHUB_TOKEN/GITHUB_REPOSITORY/PR
number aren't available — see `_post_github_comment`.

Degradation without an API key (plan 32.8): DispatchProvider constructs
lazily, so a missing/invalid PROXYAPI_KEY doesn't fail until the actual API
call — which raises inside resilience.call_with_resilience, which catches it,
retries, tries the fallback model, and finally returns ok=False. This CLI
then prints resilience.DETERMINISTIC_FAILURE_MSG to stderr and exits 1. It
never crashes.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from agent_cli.config import DEFAULT_MODEL
from agent_cli.llm.dispatch import DispatchProvider

from agent_web.services.rag.config import KNOWLEDGE_BASES
from agent_web.services.review import metrics as metrics_mod
from agent_web.services.review.pipeline import PROMPT_VERSION, run_review
from agent_web.services.review.resilience import DETERMINISTIC_FAILURE_MSG, call_with_resilience

# Cheap, reliable second rung of the ladder if the primary model fails.
FALLBACK_MODEL = "openai/gpt-4o-mini"

_GEN_KWARGS = {"max_tokens": 1500, "temperature": 0.2}


def _changed_files_from_diff(diff_text: str) -> list[str]:
    return sorted({
        line.split(" b/", 1)[-1]
        for line in diff_text.splitlines()
        if line.startswith("diff --git ")
    })


def _load_diff(args: argparse.Namespace) -> tuple[str, list[str]]:
    if args.diff_file:
        diff_text = Path(args.diff_file).read_text(encoding="utf-8")
    elif args.base and args.head:
        proc = subprocess.run(
            ["git", "diff", f"{args.base}...{args.head}"],
            capture_output=True, text=True, check=True, cwd=args.repo_root,
        )
        diff_text = proc.stdout
    else:
        raise SystemExit("Need --diff-file, or --base and --head")
    return diff_text, _changed_files_from_diff(diff_text)


def _get_project_rag() -> tuple[str | None, object, str]:
    """Best-effort project RAG context. Missing/broken index degrades to no
    context (kb=None) rather than failing the whole review."""
    try:
        from agent_web.dependencies import get_rag_index
        cfg = KNOWLEDGE_BASES["project"]
        index = get_rag_index(kb="project")
        return "project", index, cfg["backend"]
    except Exception as e:
        print(f"warning: RAG context unavailable ({e}), reviewing without it", file=sys.stderr)
        return None, None, "proxyapi"


def _format_output(result, run_id: str) -> str:
    def _fmt(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- none found"

    return (
        f"### AI Review (run `{run_id}`, model `{result.model}`)\n\n"
        f"## Potential bugs\n{_fmt(result.bugs)}\n\n"
        f"## Architectural issues\n{_fmt(result.architecture)}\n\n"
        f"## Recommendations\n{_fmt(result.recommendations)}\n"
    )


def _pr_number_from_event() -> str | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None
    try:
        data = json.loads(Path(event_path).read_text(encoding="utf-8"))
        return str(data["pull_request"]["number"])
    except Exception:
        return None


def _post_github_comment(body: str, args: argparse.Namespace) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = args.pr or _pr_number_from_event()
    if not token or not repo or not pr_number:
        print(
            "warning: --post-comment requested but GITHUB_TOKEN/GITHUB_REPOSITORY/PR number "
            "missing, skipping comment post",
            file=sys.stderr,
        )
        return
    import httpx

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    resp = httpx.post(url, headers=headers, json={"body": body}, timeout=30)
    resp.raise_for_status()


def cmd_score(args: argparse.Namespace) -> int:
    ok = metrics_mod.set_human_score(args.run_id, args.score)
    if not ok:
        print(f"run_id {args.run_id!r} not found in {metrics_mod.METRICS_PATH}", file=sys.stderr)
        return 1
    print(f"scored {args.run_id} = {args.score}")
    return 0


def cmd_review(args: argparse.Namespace, *, provider=None) -> int:
    diff_text, changed_files = _load_diff(args)
    model = args.model or DEFAULT_MODEL
    run_id = str(uuid.uuid4())[:8]

    provider = provider or DispatchProvider()
    kb, index, backend = _get_project_rag()

    usage_holder: dict = {}

    def _chat_fn(messages: list[dict], model_to_use: str) -> str:
        text, usage = provider.chat_with_stats(messages, model_to_use, **_GEN_KWARGS)
        usage_holder["usage"] = usage
        return text

    def _call(model_to_use: str):
        result = run_review(
            diff_text, changed_files, kb, model_to_use,
            chat_fn=_chat_fn, index=index, backend=backend,
        )
        if not result.ok:
            raise RuntimeError("empty or unparsable LLM response")
        return result, usage_holder.get("usage")

    attempts: list[dict] = []
    t0 = time.time()
    resilient = call_with_resilience(
        _call, model, fallback_model=FALLBACK_MODEL,
        max_retries=1, timeout_s=90.0, on_attempt=attempts.append,
    )
    latency_ms = (time.time() - t0) * 1000

    usage = resilient.usage
    metric = metrics_mod.ReviewMetric(
        ts=time.time(),
        run_id=run_id,
        pr=args.pr,
        model=resilient.model_used or model,
        prompt_version=PROMPT_VERSION,
        latency_ms=latency_ms,
        tokens=(usage.total_tokens if usage else 0),
        cost_rub=(usage.cost_rub if usage else 0.0),
        ok=resilient.ok,
        retries=resilient.retries,
        human_score=None,
    )
    if not args.dry_run:
        metrics_mod.record(metric)

    if not resilient.ok:
        print(DETERMINISTIC_FAILURE_MSG, file=sys.stderr)
        print(f"run_id={run_id}", file=sys.stderr)
        return 1

    output = _format_output(resilient.payload, run_id)
    print(output)

    if args.post_comment and not args.dry_run:
        _post_github_comment(output, args)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agent_web.services.review")
    sub = parser.add_subparsers(dest="command")

    score_p = sub.add_parser("score", help="Record a human quality score (1-5) for a run_id")
    score_p.add_argument("run_id")
    score_p.add_argument("score", type=int, choices=range(1, 6))
    score_p.set_defaults(func=cmd_score)

    parser.add_argument("--diff-file", help="Path to a unified diff file")
    parser.add_argument("--pr", help="PR number (for metrics + comment posting)")
    parser.add_argument("--base", help="Base ref/sha for --base/--head diff mode")
    parser.add_argument("--head", help="Head ref/sha for --base/--head diff mode")
    parser.add_argument("--repo-root", default=".", help="cwd for `git diff` in --base/--head mode")
    parser.add_argument("--model", help=f"Primary model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Run + print, but don't record metrics or post a comment")
    parser.add_argument("--post-comment", action="store_true", help="Post the review as a GitHub PR comment")
    parser.set_defaults(func=cmd_review)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
