<!-- source: mcp-server/project_server.py | title: project_server.py -->

"""Local MCP server exposing read-only git/filesystem facts about THIS repo's
working copy, for /help (day 31) and later /support, file-agent (day 33/34).

Runs LOCALLY (127.0.0.1:8002), not on the VPS — the VPS can't see this
machine's working tree (uncommitted changes, current branch). Repo root comes
from the PROJECT_ROOT env var, never from cwd, so it behaves the same
regardless of where the process is launched from.

Run: PROJECT_ROOT=/path/to/repo python mcp-server/project_server.py
"""
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).parent.parent)).resolve()

mcp = FastMCP("Project Tools", host="127.0.0.1")

# Never list/read these even if a caller asks — same rule day 34's fs_tools sandbox uses.
_FORBIDDEN_NAMES = {".env", ".git", ".venv", "node_modules"}
_FORBIDDEN_SUFFIXES = {".key"}


def _run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return f"git error: {result.stderr.strip() or result.stdout.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "git error: git not installed"
    except subprocess.TimeoutExpired:
        return "git error: timed out"
    except Exception as e:
        return f"git error: {e}"


@mcp.tool()
def git_current_branch() -> str:
    """Get the name of the currently checked-out git branch in the project's working copy."""
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"])


@mcp.tool()
def git_status() -> str:
    """Get `git status --short` for the project's working copy — modified/untracked files."""
    out = _run_git(["status", "--short"])
    return out if out else "working tree clean"


@mcp.tool()
def git_diff(path: str = "") -> str:
    """Get `git diff` (unstaged changes) for the project's working copy.
    Optional `path`: restrict to a single file (relative to repo root)."""
    args = ["diff"]
    if path:
        args.append(path)
    out = _run_git(args)
    return out if out else "no unstaged changes"


def _is_forbidden(rel: Path) -> bool:
    return any(
        part in _FORBIDDEN_NAMES or Path(part).suffix in _FORBIDDEN_SUFFIXES
        for part in rel.parts
    )


@mcp.tool()
def list_project_files(subdir: str = "", pattern: str = "*") -> str:
    """List files under the project repo (sandboxed to PROJECT_ROOT — cannot escape via
    '../' or absolute paths). subdir: relative directory to list (default: repo root).
    pattern: glob pattern, e.g. '*.py'."""
    base = (PROJECT_ROOT / subdir).resolve()
    if not base.is_relative_to(PROJECT_ROOT):
        return f"Error: '{subdir}' escapes the project root — refused."
    if not base.exists():
        return f"Error: '{subdir}' does not exist."

    results = []
    for p in sorted(base.glob(pattern)):
        try:
            rel = p.resolve().relative_to(PROJECT_ROOT)
        except ValueError:
            continue  # symlink escaping PROJECT_ROOT — refuse to list it
        if _is_forbidden(rel):
            continue
        results.append(str(rel) + ("/" if p.is_dir() else ""))
        if len(results) >= 200:
            results.append("... (truncated at 200)")
            break
    return "\n".join(results) if results else "(no files matched)"


if __name__ == "__main__":
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="127.0.0.1", port=8002)
