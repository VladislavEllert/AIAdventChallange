"""Day 34: pure, deterministic tool→danger-level mapping.

NO LLM call here on purpose — an LLM in the authorization path gives a
nondeterministic security decision plus per-call latency (explicit plan
rejection, see swarm-report/week07-dev-assistant-plan.md step 34.5). This is
just a lookup table keyed by tool name; the target path does not change the
verdict (a write is dangerous regardless of which in-sandbox file it targets).
"""

SAFE = "safe"
DANGEROUS = "dangerous"

# Tool name -> danger level. Anything not listed defaults to DANGEROUS
# (fail closed — an unrecognized tool never silently skips confirmation).
_DANGER_BY_TOOL: dict[str, str] = {
    "read_file": SAFE,
    "search_files": SAFE,
    "list_dir": SAFE,
    "write_file": DANGEROUS,
    "delete_file": DANGEROUS,
    # Day 35 — git_diff/git_log/git_status intentionally absent: they're never
    # register()-ed into the shared registry (see git_tools.py's naming-collision
    # docstring), so executor.py never looks them up here either.
    "git_commit": DANGEROUS,
}


def danger_level(tool_name: str, target_path: str = "") -> str:
    """Pure function of (tool name, target path) -> "safe" | "dangerous".

    `target_path` is accepted for signature stability (plan step 34.5 specifies
    the function is of tool name + path) but does not currently affect the
    verdict — no path is "more dangerous" than another once it's already
    inside the fs_tools sandbox; the operation type is what matters.
    """
    return _DANGER_BY_TOOL.get(tool_name, DANGEROUS)


def is_dangerous(tool_name: str, target_path: str = "") -> bool:
    return danger_level(tool_name, target_path) == DANGEROUS
