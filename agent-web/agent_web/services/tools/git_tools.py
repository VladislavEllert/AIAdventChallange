"""Day 35: git tools for the ritual chain (`rituals/day_report.py`) and the
`/ritual` slash command — mirrors `fs_tools.py`'s Tool(name, description,
parameters, execute, danger_level) pattern (plan step 35.2).

`git_diff`/`git_log`/`git_status` are SAFE (read-only). `git_commit` is
DANGEROUS — routed through the same confirm/executor gate day 34 built for
`write_file`/`delete_file` (see tools/confirm.py, tools/executor.py). No
`git_push` tool exists here, not even behind a flag — CLAUDE.md forbids
auto-push; a disabled/flagged tool would still be dead code inviting misuse
later, so it's simply not written (plan step 35.2, "Out of scope").

NAMING NOTE — why git_diff/git_status/git_log are NOT `register()`-ed into
the shared local-tool registry (unlike git_commit and every fs_tools entry):
`mcp-server/project_server.py` (day 31) already exposes MCP tools named
`git_status`/`git_diff`/`git_current_branch`. chat.py merges
`mcp_schemas + local_schemas` into ONE list handed to the LLM whenever
`req.use_mcp=True` — and the OpenAI API rejects a `tools` array with two
entries sharing the same function name (400). Since `services/tools/registry`
is one process-wide dict (not scoped per caller), registering same-named
tools here would collide with the MCP ones the moment this module is
imported anywhere in the process — a real regression risk for every
existing chat request with `use_mcp=True` (days 31/33/34), not just
`/ritual`. So the three read-only tools stay as plain `Tool` instances
(consistent shape, direct `.execute()` calls from `rituals/day_report.py` /
`commands_ritual.py`) without touching the shared registry. `git_commit` has
no MCP namesake, so it registers normally and gets the confirm gate.
"""
import os
import subprocess
from pathlib import Path

from agent_web.services.tools.fs_tools import resolve_in_sandbox, SandboxError
from agent_web.services.tools.registry import Tool, register

REPO_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).parents[4])).resolve()


def _run_git(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout,
    )


# ── git_diff ────────────────────────────────────────────────────────────
def _git_diff(path: str = "", staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    if path:
        try:
            resolve_in_sandbox(path)
        except SandboxError as e:
            return f"Error: {e}"
        args += ["--", path]
    try:
        result = _run_git(args)
    except subprocess.TimeoutExpired:
        return "Error: git diff timed out."
    if result.returncode != 0:
        return f"Error: git diff failed: {result.stderr.strip()}"
    return result.stdout or "(no changes)"


GIT_DIFF = Tool(
    name="git_diff",
    description="Show unstaged (or --staged) git diff, optionally scoped to one path. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Optional path to scope the diff to"},
            "staged": {"type": "boolean", "description": "Show staged diff instead of working tree (default false)"},
        },
        "required": [],
    },
    execute=_git_diff,
    danger_level="safe",
)


# ── git_log ─────────────────────────────────────────────────────────────
def _git_log(max_count: int = 10, path: str = "") -> str:
    args = ["log", f"-n{max_count}", "--oneline"]
    if path:
        try:
            resolve_in_sandbox(path)
        except SandboxError as e:
            return f"Error: {e}"
        args += ["--", path]
    try:
        result = _run_git(args)
    except subprocess.TimeoutExpired:
        return "Error: git log timed out."
    if result.returncode != 0:
        return f"Error: git log failed: {result.stderr.strip()}"
    return result.stdout or "(no commits)"


GIT_LOG = Tool(
    name="git_log",
    description="Show recent commit history (oneline), optionally scoped to one path. Read-only.",
    parameters={
        "type": "object",
        "properties": {
            "max_count": {"type": "integer", "description": "Max commits to show (default 10)"},
            "path": {"type": "string", "description": "Optional path to scope the log to"},
        },
        "required": [],
    },
    execute=_git_log,
    danger_level="safe",
)


# ── git_status ──────────────────────────────────────────────────────────
def _git_status() -> str:
    try:
        result = _run_git(["status", "--porcelain"])
    except subprocess.TimeoutExpired:
        return "Error: git status timed out."
    if result.returncode != 0:
        return f"Error: git status failed: {result.stderr.strip()}"
    return result.stdout or "(clean)"


GIT_STATUS = Tool(
    name="git_status",
    description="Show `git status --porcelain`. Read-only.",
    parameters={"type": "object", "properties": {}, "required": []},
    execute=_git_status,
    danger_level="safe",
)


# ── git_commit (DANGEROUS) ──────────────────────────────────────────────
def _git_commit(message: str, paths: list[str]) -> str:
    """Stages EXACTLY `paths` (never `git add -A`/`.`) then commits. Each path
    goes through the same sandbox+denylist as fs_tools (blocks .env/*.key/.git/
    .venv/node_modules) — a confirmed commit still can never stage a secret.
    No push — this function does not know how to push, by design."""
    if not paths:
        return "Error: no paths given — refusing to guess what to commit."
    resolved: list[Path] = []
    for p in paths:
        try:
            resolved.append(resolve_in_sandbox(p))
        except SandboxError as e:
            return f"Error: {e}"

    add_result = _run_git(["add", "--", *paths])
    if add_result.returncode != 0:
        return f"Error: git add failed: {add_result.stderr.strip()}"

    # BUG FOUND LIVE (day 35 self-test): `git commit -m msg` with no pathspec
    # commits the WHOLE index, not just what this call just `git add`-ed. If
    # something else was ALREADY staged (a leftover `git add` from earlier in
    # the session, or from another tool run) it rides along silently — the
    # "stages exactly these paths" promise only held for the `add` step, not
    # the `commit` step. Fix: `git commit -- <paths>` restricts the commit
    # itself to exactly those paths regardless of anything else staged,
    # leaving unrelated staged changes untouched in the index.
    commit_result = _run_git(["commit", "-m", message, "--", *paths])
    if commit_result.returncode != 0:
        return f"Error: git commit failed: {commit_result.stderr.strip() or commit_result.stdout.strip()}"

    sha = _run_git(["rev-parse", "--short", "HEAD"])
    sha_str = sha.stdout.strip() if sha.returncode == 0 else "?"
    return f"Committed {sha_str}: {message}\n{commit_result.stdout.strip()}"


GIT_COMMIT = Tool(
    name="git_commit",
    description=(
        "Stage exactly the given paths and create a local commit. Never pushes — "
        "push stays manual, by policy. DANGEROUS: requires human confirmation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message"},
            "paths": {
                "type": "array", "items": {"type": "string"},
                "description": "Exact repo-relative paths to stage and commit (no wildcards, no -A)",
            },
        },
        "required": ["message", "paths"],
    },
    execute=_git_commit,
    danger_level="dangerous",
)

register(GIT_COMMIT)
