"""Day 34: file-agent tools, sandboxed to REPO_ROOT.

Sandbox rule (security-critical, see plan step 34.4): resolve the candidate
path with `Path.resolve()` (follows symlinks) and check `is_relative_to`
against the resolved REPO_ROOT. A plain string-prefix check on the raw path
is bypassable by a symlink pointing outside the repo, or by `..` segments
that a naive prefix check never normalizes — `resolve()` collapses both
before the check runs.

Forbidden regardless of location-in-repo: `.env`, `*.key`, `.git/**`,
`.venv/**`, `node_modules/**` — same denylist as mcp-server/project_server.py
(day 31), kept in sync by hand since these are two different processes.
"""
import os
import shutil
import subprocess
from pathlib import Path

from agent_web.services.tools.registry import Tool, register

REPO_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).parents[4])).resolve()

_FORBIDDEN_NAMES = {".env", ".git", ".venv", "node_modules"}
_FORBIDDEN_SUFFIXES = {".key"}


class SandboxError(ValueError):
    """Raised when a path escapes REPO_ROOT or hits the forbidden denylist."""


def _is_forbidden(rel: Path) -> bool:
    return any(
        part in _FORBIDDEN_NAMES or Path(part).suffix in _FORBIDDEN_SUFFIXES
        for part in rel.parts
    )


def resolve_in_sandbox(path: str) -> Path:
    """Resolve `path` (relative to REPO_ROOT, or absolute) and enforce the sandbox.
    Raises SandboxError if it escapes REPO_ROOT or matches the denylist.
    Never uses a string-prefix check — see module docstring."""
    candidate = (REPO_ROOT / path) if not os.path.isabs(path) else Path(path)
    resolved = candidate.resolve()  # follows symlinks, collapses '..'

    if not resolved.is_relative_to(REPO_ROOT):
        raise SandboxError(f"path '{path}' escapes the repo sandbox")

    rel = resolved.relative_to(REPO_ROOT)
    if _is_forbidden(rel):
        raise SandboxError(f"path '{path}' is in the forbidden denylist (.env/*.key/.git/.venv/node_modules)")

    return resolved


# ── read_file ────────────────────────────────────────────────────────────
def _read_file(path: str, max_bytes: int = 50_000) -> str:
    p = resolve_in_sandbox(path)
    if not p.exists():
        return f"Error: '{path}' does not exist."
    if p.is_dir():
        return f"Error: '{path}' is a directory, not a file."
    data = p.read_bytes()[:max_bytes]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return f"Error: '{path}' is not valid UTF-8 (binary file?)."


register(Tool(
    name="read_file",
    description="Read a text file's contents. Path is relative to the repo root and sandboxed — cannot escape via '../' or symlinks. Refuses .env/*.key/.git/.venv/node_modules.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to repo root"},
            "max_bytes": {"type": "integer", "description": "Max bytes to read (default 50000)"},
        },
        "required": ["path"],
    },
    execute=_read_file,
    danger_level="safe",
))


# ── search_files (ripgrep) ──────────────────────────────────────────────
def _search_files(pattern: str, path: str = ".", max_results: int = 100) -> str:
    base = resolve_in_sandbox(path)
    if not shutil.which("rg"):
        return "Error: ripgrep ('rg') is not installed on this machine."
    try:
        result = subprocess.run(
            ["rg", "--line-number", "--no-heading", "--max-count", "20",
             "-g", "!.git", "-g", "!.venv", "-g", "!node_modules", "-g", "!.env", "-g", "!*.key",
             pattern, str(base)],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return "Error: ripgrep ('rg') is not installed on this machine."
    except subprocess.TimeoutExpired:
        return "Error: search timed out."

    if result.returncode not in (0, 1):  # 1 = no matches, still success
        return f"Error: rg failed: {result.stderr.strip()}"

    lines = result.stdout.splitlines()[:max_results]
    out = []
    for line in lines:
        try:
            abs_path, rest = line.split(":", 1)
            rel = Path(abs_path).resolve().relative_to(REPO_ROOT)
            out.append(f"{rel}:{rest}")
        except Exception:
            out.append(line)
    return "\n".join(out) if out else "(no matches)"


register(Tool(
    name="search_files",
    description="Search file contents for a regex pattern using ripgrep, sandboxed to the repo. Returns file:line:match lines.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "Directory to search under, relative to repo root (default '.')"},
            "max_results": {"type": "integer", "description": "Max result lines (default 100)"},
        },
        "required": ["pattern"],
    },
    execute=_search_files,
    danger_level="safe",
))


# ── list_dir ─────────────────────────────────────────────────────────────
def _list_dir(path: str = ".", pattern: str = "*") -> str:
    base = resolve_in_sandbox(path)
    if not base.exists():
        return f"Error: '{path}' does not exist."
    if not base.is_dir():
        return f"Error: '{path}' is not a directory."

    results = []
    for p in sorted(base.glob(pattern)):
        try:
            rel = p.resolve().relative_to(REPO_ROOT)
        except ValueError:
            continue  # symlink escaping REPO_ROOT — refuse to list it
        if _is_forbidden(rel):
            continue
        results.append(str(rel) + ("/" if p.is_dir() else ""))
        if len(results) >= 200:
            results.append("... (truncated at 200)")
            break
    return "\n".join(results) if results else "(empty or no matches)"


register(Tool(
    name="list_dir",
    description="List files/dirs under a repo-relative path, sandboxed. Optional glob pattern (default '*').",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory relative to repo root (default '.')"},
            "pattern": {"type": "string", "description": "Glob pattern (default '*')"},
        },
        "required": [],
    },
    execute=_list_dir,
    danger_level="safe",
))


# ── write_file (DANGEROUS — dry_run=True by default, real-write mode too) ─
def _write_file(path: str, content: str, dry_run: bool = True) -> str:
    p = resolve_in_sandbox(path)
    if dry_run:
        preview = content[:500]
        return f"[DRY RUN] would write {len(content)} bytes to '{path}':\n{preview}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to '{path}'."


register(Tool(
    name="write_file",
    description="Write (overwrite) a text file. dry_run=True (default) only previews the write — pass dry_run=false for a real write. DANGEROUS: requires human confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to repo root"},
            "content": {"type": "string", "description": "Full new file content"},
            "dry_run": {"type": "boolean", "description": "Preview only, no write (default true)"},
        },
        "required": ["path", "content"],
    },
    execute=_write_file,
    danger_level="dangerous",
))


# ── delete_file (DANGEROUS) ────────────────────────────────────────────────
def _delete_file(path: str) -> str:
    p = resolve_in_sandbox(path)
    if not p.exists():
        return f"Error: '{path}' does not exist."
    if p.is_dir():
        return f"Error: '{path}' is a directory — delete_file only removes files."
    p.unlink()
    return f"Deleted '{path}'."


register(Tool(
    name="delete_file",
    description="Delete a single file. DANGEROUS: requires human confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to repo root"},
        },
        "required": ["path"],
    },
    execute=_delete_file,
    danger_level="dangerous",
))
