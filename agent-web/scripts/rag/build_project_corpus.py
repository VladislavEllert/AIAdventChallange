"""Build the "project" RAG corpus: repo docs + our own source code
→ data/rag/corpus_project/*.md.

Also dumps FastAPI's app.openapi() schema → corpus_project/api_openapi.md —
closes the "API / data-schema docs" requirement literally, not just via prose
docs that happen to mention endpoints.
"""
import sys
from pathlib import Path

AGENT_WEB_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(AGENT_WEB_ROOT))
REPO_ROOT = AGENT_WEB_ROOT.parent

from agent_web.services.rag.config import CORPUS_PROJECT_DIR  # noqa: E402

EXCLUDE_DIR_NAMES = {".venv", "venv", "node_modules", "__pycache__", ".git"}


def _excluded(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    if path.name == ".env":
        return True
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel.startswith("data/rag/") and path.suffix == ".json":
        return True
    return False


def _collect() -> list[Path]:
    files: list[Path] = []

    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        p = REPO_ROOT / name
        if p.exists():
            files.append(p)

    mb_dir = REPO_ROOT / "memory-bank"
    if mb_dir.exists():
        files.extend(sorted(mb_dir.rglob("*.md")))

    files.extend(sorted(REPO_ROOT.glob("week-0*/**/README.md")))

    aw_pkg = REPO_ROOT / "agent-web" / "agent_web"
    if aw_pkg.exists():
        files.extend(sorted(aw_pkg.rglob("*.py")))

    ac_pkg = REPO_ROOT / "agent-cli" / "agent_cli"
    if ac_pkg.exists():
        files.extend(sorted(ac_pkg.rglob("*.py")))

    mcp_dir = REPO_ROOT / "mcp-server"
    if mcp_dir.exists():
        files.extend(sorted(mcp_dir.glob("*.py")))

    fe_src = REPO_ROOT / "agent-web" / "frontend" / "src"
    if fe_src.exists():
        files.extend(sorted(fe_src.rglob("*.ts")))
        files.extend(sorted(fe_src.rglob("*.tsx")))

    return [f for f in files if f.is_file() and not _excluded(f)]


def _slug(rel_path: str) -> str:
    return rel_path.replace("/", "__").replace(".", "_")


def parse_header(text: str):
    """Same header format as the handbook corpus — reuses build_index.py's parse_header."""
    import re
    m = re.match(r"<!--\s*source:\s*(\S+)\s*\|\s*title:\s*(.+?)\s*-->", text)
    if m:
        return m.group(1), m.group(2)
    return "", "Unknown"


def build() -> int:
    CORPUS_PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    # Clear stale files from a previous run — renamed/removed sources shouldn't linger.
    for old in CORPUS_PROJECT_DIR.glob("*.md"):
        old.unlink()

    n = 0
    for f in _collect():
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not text.strip():
            continue
        rel = f.relative_to(REPO_ROOT).as_posix()
        header = f"<!-- source: {rel} | title: {f.name} -->\n\n"
        dest = CORPUS_PROJECT_DIR / f"{_slug(rel)}.md"
        dest.write_text(header + text, encoding="utf-8")
        n += 1

    n += _dump_openapi()
    n += _dump_faq()
    print(f"Wrote {n} files → {CORPUS_PROJECT_DIR}")
    return n


def _dump_faq() -> int:
    """Copy the support FAQ (data/support/faq.md) into the corpus under its own literal
    filename `faq.md` — day 33. Kept as a separate source (not picked up by the generic
    _collect() globs) and special-cased here the same way _dump_openapi() special-cases
    the API schema, so it survives corpus rebuilds with a stable, predictable name."""
    src = REPO_ROOT / "agent-web" / "data" / "support" / "faq.md"
    if not src.exists():
        return 0
    rel = src.relative_to(REPO_ROOT).as_posix()
    header = f"<!-- source: {rel} | title: FAQ поддержки -->\n\n"
    dest = CORPUS_PROJECT_DIR / "faq.md"
    dest.write_text(header + src.read_text(encoding="utf-8"), encoding="utf-8")
    return 1


def _dump_openapi() -> int:
    """Dump FastAPI's app.openapi() schema as markdown — paths + request/response schemas."""
    from agent_web.app import create_app

    app = create_app()
    spec = app.openapi()

    info = spec.get("info", {})
    lines = [f"# API — {info.get('title', 'agent-web')} {info.get('version', '')}\n"]

    lines.append("\n## Paths\n")
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            summary = op.get("summary") or op.get("operationId") or ""
            lines.append(f"\n### {method.upper()} {path}\n{summary}\n")
            for p in op.get("parameters") or []:
                lines.append(
                    f"- param `{p.get('name')}` ({p.get('in')}) required={p.get('required', False)}\n"
                )
            if "requestBody" in op:
                lines.append("- has request body (see Schemas below)\n")

    lines.append("\n## Schemas\n")
    schemas = spec.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        lines.append(f"\n### {name}\n")
        for prop_name, prop in (schema.get("properties") or {}).items():
            ptype = prop.get("type") or prop.get("$ref") or "any"
            lines.append(f"- `{prop_name}`: {ptype}\n")

    body = "".join(lines)
    header = "<!-- source: agent-web/agent_web/app.py | title: API openapi schema -->\n\n"
    dest = CORPUS_PROJECT_DIR / "api_openapi.md"
    dest.write_text(header + body, encoding="utf-8")
    return 1


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
