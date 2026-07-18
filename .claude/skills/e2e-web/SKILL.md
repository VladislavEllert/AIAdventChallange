---
name: e2e-web
description: Drive agent-web's chat golden path in a real Chromium browser via Playwright before claiming any UI-touching task done. Use whenever a change touches agent-web/frontend/** or a backend route the chat UI calls (chat.py, sessions, models, settings) — not for pure backend/CLI/doc work with no browser surface.
---

# Skill: e2e-web

Browser self-test infra for `agent-web`. Exists because pytest with mocked providers only
proves the mocked logic runs — it has caught zero frontend-state regressions (e.g. the
"input/send button stuck disabled forever after a response" bug class — see memory note
"Drive golden path"). This skill is how an agent proves the UI actually works, not just
that the API returns 200.

## When to invoke

Before writing "done" on any task that touches:
- `agent-web/frontend/src/**` (any component, store, or API client)
- backend routes the chat page calls: `agent_web/routers/chat.py`, `sessions.py`,
  `models.py`, `settings.py`, or anything in `agent_web/services/**` reachable from those
- `agent-web/data/settings.json` (default model, etc.)

Skip for: pure CLI (`agent-cli/**` without web surface), docs, MCP-server-only changes with
no chat-visible effect, backend routes the chat UI never calls.

## Sequence

1. **Check the dev servers aren't stale zombies.** A backend/frontend process left running
   from a previous session serves old code and will make this check lie.
   ```
   lsof -i :8765 -sTCP:LISTEN   # backend
   lsof -i :5173 -sTCP:LISTEN   # vite
   ```
   If a listener's start time predates your current change, kill it (`kill <pid>`) —
   `playwright.config.ts`'s `webServer[].reuseExistingServer: true` will otherwise happily
   reuse the stale one instead of starting fresh.

2. **Run the suite** from `agent-web/frontend/`:
   ```
   npx playwright test
   ```
   `playwright.config.ts` starts (or reuses) both the backend (`../agent-web` venv
   `python __main__.py`, `AGENT_WEB_OPEN_BROWSER=0`) and the frontend (`npm run dev`) via
   its `webServer` array — no separate script needed.

3. **`golden-path.spec.ts`** covers: nickname modal → new session → switch model to
   `openai/gpt-4o-mini` via `/model` (the store's default, `ollama/qwen3:4b`, is not
   reachable from a dev machine without a local Ollama) → send a real message → assert a
   non-empty assistant reply renders → assert the input re-enables afterward. This last
   assertion is the regression guard — a stuck-disabled input is silent to pytest.
   Requires a live `PROXYAPI_KEY` (repo-root `.env`, loaded by
   `agent_cli/config.py`'s two-pass `dotenv` search) since it makes one real ProxyAPI call.

4. **If the task adds a new UI flow** (new command, new panel, new confirm modal — days
   31/33/34/35 in the week-07 plan), add a spec file next to `golden-path.spec.ts` for that
   flow's own golden path (e.g. `help-command.spec.ts`, `support-command.spec.ts`,
   `tool-confirm.spec.ts`). Don't bolt unrelated assertions onto `golden-path.spec.ts` —
   keep one spec file per flow so a failure points at what broke.

## What counts as failure

- Any assertion timeout — Playwright's default trace-on-first-retry plus the screenshot
  captured automatically on failure are enough to diagnose from `e2e-results/` and
  `frontend/e2e-report/` (HTML report — open with `npx playwright show-report`).
- `webServer` failing to start (check the inlined `[WebServer]` log lines in the test
  output first — a `ModuleNotFoundError` or "address already in use" there means an
  environment problem, not an app bug).
- A prior run's stale zombie process serving old code and getting reused — always do step 1.

Passing pytest with `status: done` on a UI-touching phase but skipping this step is not
"done" — it's "partial", per `.claude/agents/week07-dev-assistant.md`'s Return contract.

## Where output goes

- Screenshots (failure only, auto-captured): `agent-web/frontend/e2e-results/`.
- Traces (on first retry): same directory, `.zip` per failed test — open with
  `npx playwright show-trace <path>`.
- HTML report: `agent-web/frontend/e2e-report/` — `npx playwright show-report` to view.
- Per-day durable evidence for the course README: copy a representative screenshot into
  `week-07/day-NN/screens/` if the plan's acceptance criteria for that day call for one
  (see plan's "Сквозные (каждая фаза)" acceptance criteria).
- None of `e2e-results/`, `e2e-report/` need to be committed — they're regenerated per run.
  Add them to `agent-web/frontend/.gitignore` if not already ignored.
