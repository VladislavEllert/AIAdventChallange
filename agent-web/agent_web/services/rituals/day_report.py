"""Day 35: the actual task this ritual automates — writing the end-of-day
progress-line in root README.md + memory-bank/progress.md by hand, every day,
without missing a file, inventing a video link, or breaking the markdown
table. See week-07/day-35/README.md for the full problem statement.

Three plain-function roles, chained by `run_ritual()` — no subagent
framework, no parallelism (plan's explicit call, see swarm-report/
week07-dev-assistant-plan.md "Out of scope"):

  collect()  -> gathers ground truth: git diff, changed files, review metrics.
                Pure Python, no LLM call — same reasoning as danger.py: nothing
                here is a judgment call, it's just reading state.
  draft()    -> the one LLM role. Writes a candidate progress-table row from
                what collect() gathered. System prompt forbids inventing a
                video link.
  verify()   -> pure Python gate, no LLM call (same reasoning as collect()):
                table format, link presence, and the no-hallucinated-video
                check are all mechanical string checks — an LLM verifying
                its own sibling call's output is a nondeterministic judge for
                a deterministic question, strictly worse here than a regex.
  build_patch() -> given an approved row, computes the new README.md /
                progress.md content (insert-or-replace by day number) plus a
                unified diff string for display. Does NOT write to disk —
                callers (commands_ritual.py for the chat flow, __main__.py
                for headless) own the actual write + confirm + commit.

Any live LLM call in this module MUST use MODEL (openai/gpt-4o-mini) — see
CLAUDE.md's model constraint for week 7. `draft()` takes `chat_fn` as an
injected dependency (same shape as review/pipeline.py's ChatFn) so tests
never make a live call.
"""
import difflib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

MODEL = "openai/gpt-4o-mini"

_DAY_ROW_RE_TMPL = r"^\|\s*07\s*\|\s*{day}\s*\|"
_ANY_DAY_ROW_RE = re.compile(r"^\|\s*07\s*\|\s*(\d{2})\s*\|")

DRAFTER_SYSTEM_PROMPT = (
    "You draft ONE row for a markdown progress table documenting a daily coding "
    "challenge. The table has exactly 6 columns, in this exact order: "
    "Неделя (week number) | День (day number) | Задача (what was built TODAY, "
    "terse, Russian, technical) | Статус (`done` or `todo`) | Код (a markdown "
    "link to the day's code folder) | Видео (a video link, or the literal word "
    "`todo` if no video was recorded).\n\n"
    "The diff you're given is sorted NEW-FILES-FIRST (marked '=== NEW FILE: "
    "<path> ===') because this repo can go several days between commits — most "
    "of a raw `git diff` is often PRIOR days' work, not today's. Base Задача "
    "STRICTLY on the NEW FILE entries — those are what was actually built "
    "today. Do NOT mention pre-existing commands/files as if they were built "
    "today just because they appear elsewhere in the diff or file list; only "
    "describe something as new work if it corresponds to a NEW FILE entry.\n\n"
    "Код column MUST be a link in the exact form "
    "`[week-<WW>/day-<DD>](week-<WW>/day-<DD>/)` using the week/day numbers "
    "given below (e.g. `[week-07/day-35](week-07/day-35/)`) — never link to a "
    "package/module folder instead.\n\n"
    "CRITICAL RULE: you are given the day's real git diff, changed files, and "
    "metrics as ground truth. You MUST NOT invent facts not present in that "
    "ground truth. In particular, NEVER write a video URL in the Видео column "
    "unless the ground truth text explicitly contains one — if it doesn't, "
    "the Видео column MUST be exactly `todo`.\n\n"
    "Output ONLY the single markdown DATA row, nothing else: no preamble, no "
    "explanation, no code fence, no header row, and no `|---|---|` separator "
    "row — just the one line of real data, starting and ending with `|`."
)


@dataclass
class Collected:
    week: str
    day: str
    diff: str
    changed_files: list[str]
    metrics_summary: str


@dataclass
class VerifyResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class Patch:
    files: dict[str, str]  # repo-relative path -> new full file content
    diff_text: str  # unified diff across all touched files, for display


ChatFn = Callable[[list[dict], str], str]


# ── collect() ─────────────────────────────────────────────────────────────
def collect(
    repo_root: Path, week: str, day: str, metrics_path: Path | None = None,
    diff_budget_chars: int = 8000, per_file_budget_chars: int = 1200,
) -> Collected:
    """No LLM call. Reads real git state + (optionally) review metrics.

    A repo that hasn't committed in days (this project's whole week 31-34 sat
    uncommitted while day 35 was built — see git status) can have an 80+ file,
    600KB+ `git diff`. A flat `diff[:N]` slice is dominated by whatever git
    happens to print first (alphabetical: AGENTS.md, README.md, ... — NOT
    today's actual new files) — caught live during the day-35 dry run: the
    drafter described day 32's work because the diff slice never reached any
    day-35 file. Fix: sort changed files untracked/added-first (brand-new
    files are the strongest "this session's work" signal, existing modified
    files trail), then build the diff by giving each file its own capped
    budget in that priority order — so day-specific new files are always
    represented, not just whichever file sorts first alphabetically."""
    status_proc = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, timeout=15,
    )
    entries: list[tuple[str, str]] = []
    for line in status_proc.stdout.splitlines():
        if not line.strip():
            continue
        code, path = line[:2], line[3:].strip()
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        entries.append((code, path))

    entries.sort(key=lambda e: (0 if "?" in e[0] or "A" in e[0] else 1, e[1]))
    changed_files = [p for _, p in entries]

    diff_parts: list[str] = []
    budget = diff_budget_chars
    for code, path in entries:
        if budget <= 0:
            break
        if "?" in code:
            try:
                content = (repo_root / path).read_text(encoding="utf-8", errors="replace")
                snippet = f"=== NEW FILE: {path} ===\n{content[:per_file_budget_chars]}\n"
            except Exception:
                snippet = f"=== NEW FILE: {path} === (binary or unreadable)\n"
        else:
            file_diff = subprocess.run(
                ["git", "diff", "--", path], cwd=repo_root, capture_output=True, text=True, timeout=15,
            )
            if not file_diff.stdout:
                continue
            snippet = f"=== {path} ===\n{file_diff.stdout[:per_file_budget_chars]}\n"
        diff_parts.append(snippet)
        budget -= len(snippet)
    diff_text = "".join(diff_parts)

    metrics_summary = "(no review metrics)"
    try:
        from agent_web.services.review import metrics as metrics_mod
        records = metrics_mod.read_all(metrics_path) if metrics_path else metrics_mod.read_all()
        if records:
            agg = metrics_mod.aggregate(records)
            metrics_summary = (
                f"{agg.count} review runs recorded; p50 latency {agg.p50_latency_ms:.0f}ms; "
                f"avg cost {agg.avg_cost_rub:.4f}RUB; {agg.pct_successful:.0f}% successful"
            )
    except Exception:
        pass  # metrics are best-effort context for the drafter, never fatal

    return Collected(
        week=week, day=day, diff=diff_text, changed_files=changed_files,
        metrics_summary=metrics_summary,
    )


# ── draft() ──────────────────────────────────────────────────────────────
def draft(collected: Collected, *, chat_fn: ChatFn, model: str = MODEL) -> str:
    user_content = (
        f"Week: {collected.week}, Day: {collected.day}\n\n"
        f"## Changed files (git status --porcelain)\n"
        + ("\n".join(collected.changed_files) or "(none)") + "\n\n"
        f"## Review metrics context\n{collected.metrics_summary}\n\n"
        f"## git diff (working tree, new-files-first, per-file budgeted — see collect())\n"
        f"```diff\n{collected.diff[:9000]}\n```\n"
    )
    messages = [
        {"role": "system", "content": DRAFTER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    raw = chat_fn(messages, model).strip()
    return _extract_data_row(raw)


def _extract_data_row(raw: str) -> str:
    """Defensive post-processing: despite the system prompt telling it not to,
    the model sometimes still echoes the header row + `|---|` separator before
    the real data row (caught live during the day-35 dry run). Take the LAST
    non-empty line that isn't a separator (`---`) or the literal header
    (contains 'Неделя' as a whole cell) — that's always the actual data row
    when the model over-completes; a no-op when it already followed the
    instruction and produced exactly one line."""
    candidates = [
        line.strip() for line in raw.splitlines()
        if line.strip().startswith("|") and "---" not in line and "Неделя" not in line
    ]
    return candidates[-1] if candidates else raw


# ── verify() ─────────────────────────────────────────────────────────────
def verify(row: str, collected: Collected) -> VerifyResult:
    errors: list[str] = []
    row = row.strip()

    if not (row.startswith("|") and row.endswith("|")):
        errors.append("row does not start/end with '|' — not a valid table row")
        return VerifyResult(ok=False, errors=errors)

    cells = [c.strip() for c in row.split("|")[1:-1]]
    if len(cells) != 6:
        errors.append(f"expected 6 columns (Неделя/День/Задача/Статус/Код/Видео), got {len(cells)}")
        return VerifyResult(ok=False, errors=errors)

    week_cell, day_cell, task_cell, status_cell, code_cell, video_cell = cells

    if status_cell not in ("done", "todo"):
        errors.append(f"Статус must be 'done' or 'todo', got {status_cell!r}")

    if not re.search(r"\[.+?\]\(.+?\)", code_cell):
        errors.append("Код column has no markdown link — missing link")

    # Regression: an empty/near-empty Задача cell passed the structural checks
    # above (still 6 columns, still a valid link, still done/todo) and silently
    # overwrote a real, detailed existing row with a blank one — reproduced
    # live when collect() found nothing to report and draft() had no facts to
    # work with. A day-progress line with no actual description is useless
    # regardless of table-format validity, so reject it explicitly.
    if len(task_cell) < 20:
        errors.append(
            f"Задача column is empty or too short ({len(task_cell)} chars) — "
            "collect() likely found nothing to report; refusing to overwrite "
            "an existing row with a near-blank one"
        )

    if video_cell != "todo":
        # No automated source of truth for video links exists anywhere in this
        # pipeline — collect() never gathers one. Any non-'todo' claim here is
        # by construction unverifiable, so it's treated as a hallucination
        # regardless of what it says (see module docstring, CRITICAL RULE).
        errors.append(
            f"Видео column claims {video_cell!r} but no video evidence was collected — "
            "rejecting a claim that would be a hallucinated link (CLAUDE.md: never invent a video URL)"
        )

    return VerifyResult(ok=not errors, errors=errors)


# ── build_patch() ────────────────────────────────────────────────────────
def _upsert_row(table_text: str, day: str, new_row: str) -> str:
    lines = table_text.splitlines()
    out: list[str] = []
    replaced = False
    last_day_row_idx = None
    for i, line in enumerate(lines):
        m = _ANY_DAY_ROW_RE.match(line)
        if m:
            last_day_row_idx = len(out)
            if m.group(1) == day:
                out.append(new_row)
                replaced = True
                continue
        out.append(line)
    if not replaced:
        insert_at = (last_day_row_idx + 1) if last_day_row_idx is not None else len(out)
        out.insert(insert_at, new_row)
    return "\n".join(out) + ("\n" if table_text.endswith("\n") else "")


def build_patch(repo_root: Path, day: str, row: str) -> Patch:
    """Computes new content for root README.md + memory-bank/progress.md
    (insert-or-replace the day's row). Does not write anything to disk."""
    targets = ["README.md", "memory-bank/progress.md"]
    files: dict[str, str] = {}
    diff_parts: list[str] = []

    for rel in targets:
        path = repo_root / rel
        old_content = path.read_text(encoding="utf-8") if path.exists() else ""
        new_content = _upsert_row(old_content, day, row)
        files[rel] = new_content
        diff_parts.append(
            "".join(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel}", tofile=f"b/{rel}",
            ))
        )

    return Patch(files=files, diff_text="\n".join(p for p in diff_parts if p))


@dataclass
class RitualResult:
    collected: Collected
    row: str
    verify_result: VerifyResult
    patch: Patch | None


def run_ritual(repo_root: Path, week: str, day: str, *, chat_fn: ChatFn, model: str = MODEL) -> RitualResult:
    """Runs collect -> draft -> verify -> (build_patch if verified). Never
    writes to disk and never commits — that's the caller's job, gated on
    human confirmation (commands_ritual.py for chat, main() below headless)."""
    collected = collect(repo_root, week, day)
    if not collected.changed_files:
        # Nothing for collect() to summarize (e.g. repo already clean/committed) —
        # don't let draft() invent a row from zero facts. Reproduced live: an
        # empty-facts draft passed the table-format checks and overwrote a real,
        # detailed existing row with a blank one.
        vr = VerifyResult(
            ok=False,
            errors=["collect() found no changed files — nothing to report, refusing to draft a row"],
        )
        return RitualResult(collected=collected, row="(нет изменений для отчёта)", verify_result=vr, patch=None)
    row = draft(collected, chat_fn=chat_fn, model=model)
    vr = verify(row, collected)
    patch = build_patch(repo_root, day, row) if vr.ok else None
    return RitualResult(collected=collected, row=row, verify_result=vr, patch=patch)


# ── headless CLI: python -m agent_web.services.rituals.day_report ─────────
def _default_repo_root() -> Path:
    # agent-web/agent_web/services/rituals/day_report.py -> repo root is 4 parents up
    return Path(__file__).resolve().parents[4]


def _default_chat_fn() -> ChatFn:
    from agent_cli.llm.dispatch import DispatchProvider

    provider = DispatchProvider()

    def _chat_fn(messages: list[dict], model: str) -> str:
        text, _usage = provider.chat_with_stats(messages, model, max_tokens=800, temperature=0.2)
        return text

    return _chat_fn


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m agent_web.services.rituals.day_report")
    parser.add_argument("day", help="Two-digit day number, e.g. 35")
    parser.add_argument("--week", default="07", help="Two-digit week number (default 07)")
    parser.add_argument("--dry-run", action="store_true", help="Show the diff, never write or commit")
    args = parser.parse_args(argv)

    repo_root = _default_repo_root()
    result = run_ritual(repo_root, args.week, args.day, chat_fn=_default_chat_fn())

    print(f"\n--- drafted row (day {args.day}) ---")
    print(result.row)

    if not result.verify_result.ok:
        print("\n--- verifier REJECTED this draft ---", flush=True)
        for e in result.verify_result.errors:
            print(f"  - {e}")
        return 1

    print("\n--- verifier OK ---")
    print("\n--- patch diff ---")
    print(result.patch.diff_text or "(no diff — content unchanged)")

    if args.dry_run:
        print("\n[--dry-run] not writing, not committing.")
        return 0

    answer = input("\nApply this patch and commit locally (never pushes)? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted by user — nothing written.")
        return 1

    for rel, content in result.patch.files.items():
        (repo_root / rel).write_text(content, encoding="utf-8")
    print("Wrote:", ", ".join(result.patch.files.keys()))

    paths = list(result.patch.files.keys())
    add_proc = subprocess.run(["git", "add", "--", *paths], cwd=repo_root, capture_output=True, text=True)
    if add_proc.returncode != 0:
        print(f"git add failed: {add_proc.stderr.strip()}")
        return 1
    commit_msg = f"docs(week-{args.week}): ritual progress-line for day {args.day}"
    commit_proc = subprocess.run(
        ["git", "commit", "-m", commit_msg], cwd=repo_root, capture_output=True, text=True,
    )
    if commit_proc.returncode != 0:
        print(f"git commit failed: {commit_proc.stderr.strip() or commit_proc.stdout.strip()}")
        return 1
    print(commit_proc.stdout.strip())
    print("\nDone. Push is manual, by policy — this ritual never pushes.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
