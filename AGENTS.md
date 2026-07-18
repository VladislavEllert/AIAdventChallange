# AGENTS.md — dev-loop harness (ellert-harness)

> Entry point for the `/plan → /build → /review → /debug` harness, ported from
> `ellert-harness` (2026-07-18). `CLAUDE.md` stays the primary session config (course rules,
> workflow phases, stack) — read it first, always. This file only documents the harness layer.

---

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python — FastAPI (`agent-web/`), stdlib CLI (`agent-cli/`) |
| Frontend | React (`agent-web/frontend/`) |
| MCP | FastMCP server on VPS (`mcp-server/`) |
| RAG | Ollama embeddings, JSON vector index (`agent-web/scripts/rag/`) |

Fixed decisions: see `memory-bank/principles.md` and per-week `memory-bank/lessons/`. Don't
change stack/provider choices (ProxyAPI, Ollama, model ids) without discussion — see
`CLAUDE.md` §Стек и окружение.

---

## Memory Bank

Entry: `memory-bank/index.md` → `progress.md` / `00-overview.md` / `principles.md`. Harness
agents read `.memory-bank/` (symlinked to `memory-bank/`) — same content, two paths.

---

## Dev-loop harness (`/plan → /build → /review → /debug`)

Same as upstream `ellert-harness` — see `.agents/skills/{plan,build,review,debug}/SKILL.md`.
**This project's workflow phases (`CLAUDE.md` §Workflow) still apply on top**: no plan before
discussion is done, no code before explicit "go". `/plan` writes the plan; it does not skip the
discussion phase.

| Command | What it does |
| --- | --- |
| `/plan "<feature>"` | `planner` + `skeptic` argue, read memory bank, write `swarm-report/<slug>-plan.md` |
| `/build <slug>` | Routes `affected_files` to exec-agents (none yet — see below), runs tests |
| `/review <slug>` | `reviewer` checks diff against plan/acceptance criteria |
| `/debug "<error>"` | `debugger`: reproduce → hypothesis ladder → root cause → minimal fix |

### Exec-agents

None written yet — this harness ships only the stack-agnostic role agents (`planner`,
`skeptic`, `reviewer`, `debugger`, `describer`, `design-verifier`). Write a project-specific
exec-agent (`.claude/agents/<name>.md`) when a scope needs one (e.g. a `week-07` agent for the
new challenge project).

**Exec-routing for `/build`:**

| Scope | Agent |
| --- | --- |
| `agent-web/**` | Ask user — no dedicated exec-agent yet |
| `week-07/**` (or new week-7 project folder) | Ask user — no dedicated exec-agent yet |
| Infra/config with no owning agent | Ask the user which agent owns it |

---

## TERSE OUTPUT convention for subagents

Caveman mode does not propagate into spawned subagents automatically. Every file in
`.claude/agents/*.md` starts with a TERSE OUTPUT block — copy it into new agent files.

---

## Token-cost discipline

- Don't spawn a subagent for what a direct Read/Grep/Bash answers.
- `/compact` mid-task when context balloons; `/clear` on unrelated task switch.
- Avoid `general-purpose` subagent for narrow tasks — use `Explore` or a project exec-agent.
- Cap fix-loop iterations (`design-verify-loop` caps at 4).

---

## Git discipline

- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`). Atomic commits.
- Commits already written in English (see recent `git log`) — no enforcement hook needed.
