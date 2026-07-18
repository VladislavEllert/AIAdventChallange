"""Day 32.1: AI PR review pipeline. Diff-in, ReviewResult-out.

No GitHub API calls happen in this module — that's __main__.py's job
(--post-comment). This module is pure: parse the unified diff, pull RAG
context by filename/symbol, build the prompt, hand it to an injected
`chat_fn`, parse the three-section reply. The actual LLM call (with
timeout/retry/fallback) is resilience.py's job — `chat_fn` here is just a
plain `(messages, model) -> str` callable so tests can stub it with zero
provider/network dependency.
"""
from dataclasses import dataclass, field
from typing import Callable
import re

from agent_web.services.rag.retriever import search as rag_search

PROMPT_VERSION = "v1"
PROMPT_VERSION_V2 = "v2_strict"

SYSTEM_PROMPT = (
    "You are an experienced code reviewer for this project: agent-web (FastAPI + React "
    "AI chat app) and agent-cli (its shared Python core, providers/sessions/config). "
    "Review the unified diff below. If project knowledge-base excerpts are provided, use "
    "them for context — they may show this project's own conventions or past bugs of the "
    "same shape. Respond in exactly three sections, using these EXACT markdown headers, "
    "each a bulleted list (write a single line '- none found' if a section has nothing):\n\n"
    "## Potential bugs\n## Architectural issues\n## Recommendations\n\n"
    "Be concrete: cite file paths and line numbers from the diff. Do not invent issues "
    "that aren't supported by the diff — a clean diff with no real issues should get "
    "'- none found' in all three sections."
)

# Day 35.6: second prompt version, compared against v1 on the same 4 fixtures
# (review_eval/fixtures/, results appended to review_eval/results_day32.md —
# never overwritten, so both baselines stay visible). v1 missed fixture 03
# (httpx trust_env/SOCKS bug) in both day-32 and day-33 eval runs — v2 adds an
# explicit checklist of this project's own recurring bug shapes (all drawn
# from real bugs documented in week 6-7's tickets/FAQ, not invented for the
# prompt) and asks for a one-line justification per bug, on the theory that
# naming the exact failure shape raises recall on it without just telling the
# model to "try harder" (which wouldn't reproduce or generalize).
SYSTEM_PROMPT_V2_STRICT = (
    "You are an experienced code reviewer for this project: agent-web (FastAPI + React "
    "AI chat app) and agent-cli (its shared Python core, providers/sessions/config). "
    "Review the unified diff below. If project knowledge-base excerpts are provided, use "
    "them for context — they may show this project's own conventions or past bugs of the "
    "same shape.\n\n"
    "Pay special attention to these bug shapes that have actually recurred in this "
    "project's history — check the diff against EACH of them explicitly before writing "
    "your answer:\n"
    "1. Resource/env resolution: `.env`/config loaded relative to the WRONG base path "
    "(e.g. frame-based or cwd-based resolution picking the wrong file).\n"
    "2. `isinstance(x, SomeConcreteClass)` checks that break once `x` is wrapped by a "
    "decorator/dispatcher class (e.g. a resilience or provider wrapper).\n"
    "3. HTTP clients (`httpx`, `requests`) that silently inherit `trust_env` from the OS "
    "environment (proxy env vars) without an explicit `trust_env=False` where isolation "
    "is required.\n"
    "4. Bare/broad `except:` or `except Exception:` blocks that swallow an error without "
    "logging or re-raising, hiding a resource leak or partial failure.\n"
    "5. A filesystem/path operation that trusts a string path without `Path.resolve()` + "
    "an `is_relative_to()` sandbox check (traversal via `..` or a symlink).\n\n"
    "Respond in exactly three sections, using these EXACT markdown headers, each a "
    "bulleted list (write a single line '- none found' if a section has nothing):\n\n"
    "## Potential bugs\n## Architectural issues\n## Recommendations\n\n"
    "Be concrete: cite file paths and line numbers from the diff, and for each bug add a "
    "short justification of WHICH shape above (or another concrete reason) makes it a bug. "
    "Do not invent issues that aren't supported by the diff — a clean diff with no real "
    "issues should get '- none found' in all three sections. Flagging a pure refactor "
    "(renames, extracted functions, no behavior change) as a bug is a false positive — "
    "don't do it just to have something to say."
)

PROMPT_VERSIONS: dict[str, str] = {
    PROMPT_VERSION: SYSTEM_PROMPT,
    PROMPT_VERSION_V2: SYSTEM_PROMPT_V2_STRICT,
}


# --- diff parsing ------------------------------------------------------------


@dataclass
class Hunk:
    new_start: int
    added_lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    hunks: list[Hunk] = field(default_factory=list)

    def added_line_numbers(self) -> list[int]:
        return [ln for h in self.hunks for ln, _ in h.added_lines]


_DIFF_GIT_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_diff(diff_text: str) -> list[FileDiff]:
    """Parse a unified diff (as produced by `git diff`) into per-file hunks
    with new-file line numbers for every added ('+') line. No LLM call."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    current_hunk: Hunk | None = None
    new_lineno = 0

    for line in diff_text.splitlines():
        m = _DIFF_GIT_RE.match(line)
        if m:
            current = FileDiff(path=m.group(2))
            files.append(current)
            current_hunk = None
            continue

        hm = _HUNK_RE.match(line)
        if hm and current is not None:
            new_lineno = int(hm.group(1))
            current_hunk = Hunk(new_start=new_lineno)
            current.hunks.append(current_hunk)
            continue

        if current_hunk is None or current is None:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            current_hunk.added_lines.append((new_lineno, line[1:]))
            new_lineno += 1
        elif line.startswith("-"):
            pass  # removed line — doesn't consume a new-file line number
        else:
            new_lineno += 1

    return files


_SYMBOL_RE = re.compile(r"^\s*(?:def|class)\s+(\w+)")


def build_rag_queries(files: list[FileDiff], cap: int = 5) -> list[str]:
    """RAG queries by filename/symbol: the changed path itself, plus
    `<path> <symbol>` for every def/class introduced in the diff."""
    queries: list[str] = []
    for f in files:
        queries.append(f.path)
        for h in f.hunks:
            for _, text in h.added_lines:
                m = _SYMBOL_RE.match(text)
                if m:
                    queries.append(f"{f.path} {m.group(1)}")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:cap]


def gather_rag_context(files: list[FileDiff], kb: str | None, index, backend: str, top_k: int = 3) -> str:
    if not kb or not index:
        return ""
    parts: list[str] = []
    seen_chunks: set[str] = set()
    for q in build_rag_queries(files):
        hits, _ = rag_search(q, index, top_k=top_k, backend=backend)
        for chunk, score in hits:
            if chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk.chunk_id)
            parts.append(f"[{chunk.source}] score={score:.3f}\n{chunk.text[:500]}")
    return "\n\n---\n".join(parts)


# --- prompt + response parsing -----------------------------------------------


def build_prompt(
    diff_text: str, changed_files: list[str], rag_context: str, prompt_version: str = PROMPT_VERSION,
) -> list[dict]:
    system_prompt = PROMPT_VERSIONS.get(prompt_version, SYSTEM_PROMPT)
    user_parts = [f"## Changed files\n{', '.join(changed_files) or '(none)'}"]
    if rag_context:
        user_parts.append(f"## Project knowledge-base context\n{rag_context}")
    user_parts.append(f"## Diff\n```diff\n{diff_text}\n```")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


_SECTION_HEADERS = {
    "bugs": re.compile(r"^#+\s*potential bugs\s*$", re.I),
    "architecture": re.compile(r"^#+\s*architectural issues\s*$", re.I),
    "recommendations": re.compile(r"^#+\s*recommendations\s*$", re.I),
}
_NONE_FOUND_RE = re.compile(r"^-?\s*none found\s*$", re.I)


def parse_sections(text: str) -> tuple[list[str], list[str], list[str]]:
    """Split the LLM response into (bugs, architecture, recommendations)
    bullet lists, keyed off the three exact markdown headers."""
    sections: dict[str, list[str]] = {"bugs": [], "architecture": [], "recommendations": []}
    current_key: str | None = None
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        matched_header = False
        for key, pat in _SECTION_HEADERS.items():
            if pat.match(stripped):
                current_key = key
                matched_header = True
                break
        if matched_header:
            continue
        if current_key is None or not stripped:
            continue
        if _NONE_FOUND_RE.match(stripped):
            continue
        if stripped.startswith(("- ", "* ")):
            sections[current_key].append(stripped[2:].strip())
        else:
            sections[current_key].append(stripped)
    return sections["bugs"], sections["architecture"], sections["recommendations"]


@dataclass
class ReviewResult:
    ok: bool
    bugs: list[str] = field(default_factory=list)
    architecture: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_text: str = ""
    model: str = ""


ChatFn = Callable[[list[dict], str], str]


def run_review(
    diff_text: str,
    changed_files: list[str],
    kb: str | None,
    model: str,
    *,
    chat_fn: ChatFn,
    index=None,
    backend: str = "proxyapi",
    prompt_version: str = PROMPT_VERSION,
) -> ReviewResult:
    """Pure diff-in, ReviewResult-out.

    `chat_fn(messages, model) -> str` is injected by the caller: resilience.py
    wraps the real provider call with retry/fallback around this function;
    tests inject a stub with no network. ok=False (empty raw_text) on an
    empty/unparsable LLM response — the caller (CLI) is responsible for the
    nonzero exit code, this module just reports it.

    `prompt_version` selects the system prompt (see PROMPT_VERSIONS, day
    35.6) — defaults to PROMPT_VERSION ("v1"), the one CI actually uses;
    "v2_strict" is opt-in for eval comparison, not the production default.
    """
    files = parse_diff(diff_text)
    rag_context = gather_rag_context(files, kb, index, backend)
    messages = build_prompt(diff_text, changed_files, rag_context, prompt_version=prompt_version)
    text = chat_fn(messages, model)

    if not text or not text.strip():
        return ReviewResult(ok=False, raw_text=text or "", model=model)

    bugs, architecture, recommendations = parse_sections(text)
    return ReviewResult(
        ok=True,
        bugs=bugs,
        architecture=architecture,
        recommendations=recommendations,
        raw_text=text,
        model=model,
    )
