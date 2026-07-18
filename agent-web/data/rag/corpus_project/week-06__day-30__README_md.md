<!-- source: week-06/day-30/README.md | title: README.md -->

# Day 30 — Private service over the network

## Видео

[Видео дня](https://drive.google.com/drive/folders/1clLB0Q5h68tDx2e6xf_AcQwMHgRS9KW4?usp=share_link) (папка со всеми видео недели 6)

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/__main__.py`](../../agent-web/__main__.py) | Host/port/reload from env, defaults to `0.0.0.0:8765`, no auto-reload |
| [`agent-web/agent_web/services/rate_limit.py`](../../agent-web/agent_web/services/rate_limit.py) | Simple per-IP sliding-window limiter |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Rate limit wired onto `/chat/stream` via `Depends` |
| [`agent-web/agent_web/app.py`](../../agent-web/agent_web/app.py) | Serves the prod build same-origin (SPA fallback) — unchanged, already there since day 15 |
| [`agent-web/tests/test_concurrency.py`](../../agent-web/tests/test_concurrency.py), [`test_rate_limit.py`](../../agent-web/tests/test_rate_limit.py) | Parallel-request and rate-limit coverage |
| [`week-06/WINDOWS_SETUP.md`](../WINDOWS_SETUP.md) (§ШАГ 11) | Full runbook for standing this up on the Windows box |

## Task

Deploy as a service: HTTP API, chat, network access, stability under several requests, basic
limits (rate limit / max context).

## Scope decision (per your call earlier this session)

The Windows PC becomes the permanent host for the **whole app** (backend + frontend), not just
Ollama/ComfyUI — you said you'll `git clone` this repo onto it and run it there yourself, this
Mac session's job is to get the code ready and prove it works. So this day is: prod build,
env-driven host binding, rate limiting, real concurrency test — all verified on the Mac (acting
as a stand-in for the eventual Windows host, same code path either way) — plus a runbook
(`WINDOWS_SETUP.md` §ШАГ 11) for you to actually do the Windows deploy.

## What was done

**Host binding.** `__main__.py` read `AGENT_WEB_HOST`/`AGENT_WEB_PORT`/`AGENT_WEB_RELOAD` from
env instead of hardcoding `127.0.0.1` + `reload=True`. Defaults changed to `0.0.0.0:8765`,
`reload=False` — this is meant to run as a standing service now, not a dev convenience (use
`uvicorn ... --reload` directly while actively developing).

**Prod build.** `npm run build` → `agent_web/static/`, served same-origin by FastAPI (this
serving code already existed since day 15 — nothing to build there, just exercised it for real
this time instead of reverting the build artifacts like day 27 did).

**Rate limiting.** Simple in-memory per-IP sliding window (30 req/60s), no external dependency
(`slowapi` would be overkill for a home-LAN service that isn't internet-facing — this is a
courtesy limiter against a runaway client, not a security control, and the plan explicitly said
not to over-engineer it).

## Live verification (all against the real prod build + real Ollama, not mocked)

- **Prod build serves correctly:** `npm run build`, restarted via `python __main__.py`
  (env-driven, no `--reload`), confirmed `0.0.0.0:8765` binding, same-origin `/api/*` +
  `/assets/*` all 200, reachable over LAN (`http://192.168.0.37:8765/`), Playwright screenshots
  of the prod build match the dev build pixel-for-pixel on both viewports.
- **Real chat through the prod server:** `ollama/qwen3:4b`, real SSE stream, real response.
- **3 real parallel requests against live Ollama** (not TestClient, actual curl + actual Windows
  box): all 3 succeeded, correct isolated answers per session (no cross-talk), no crash.
  **Honest finding:** each generation's own `elapsed_ms` was ~2s, but total wall time per
  request was ~17-21s — Ollama serializes on the single GPU, so "parallel" really means
  "queued," exactly as the plan warned. Not a bug, just documented instead of glossed over.
- **Concurrency test suite** (`test_concurrency.py`) exercises the same thing with mocked
  provider + `threading` — 5 simultaneous sessions, asserts each session's stored history only
  contains its own message (would catch the FastAPI dependency system leaking state across
  concurrent requests, which it doesn't).
- **Rate limiter unit-tested** with a shrunk window (see below for why) — allows under the
  limit, 429s over it, old hits age out of the sliding window correctly.

## A real bug found writing the rate-limit test

The first version of `test_blocks_after_limit_exceeded` used the real `MAX_REQUESTS=30` against
the real `WINDOW_S=60`. It failed — not because the limiter is broken, but because each
streaming call through `TestClient` takes real wall-clock time (~4s: full SSE body consumption,
invariant checks, session save), so by request #16 the test had already run for over 60
seconds and the earliest hits were aging out of the window before the count ever reached 30.
Fixed by monkeypatching `MAX_REQUESTS`/`WINDOW_S` down to values that isolate the *counting
logic* from the *real clock* — the test was fighting real time instead of testing the limiter.

## Verification

- 47/47 `agent-web` tests green (was 43 after day 29 — added `test_rate_limit.py` (3) and
  `test_concurrency.py` (1)).
- 176/176 `agent-cli` tests unaffected.

## Honest gaps

- **Not actually deployed on the Windows box** — this Mac session doesn't have terminal access
  there. Everything above was verified on the Mac running the exact same code path (same
  `__main__.py`, same prod build, hitting the real Windows Ollama over LAN) — the runbook in
  `WINDOWS_SETUP.md` §ШАГ 11 has the concrete steps for you to run it there.
- **No autostart on Windows reboot** — same honest caveat as ComfyUI from the original setup:
  this isn't a Windows service, it's a process that needs a terminal open (or `Task Scheduler`,
  documented as an option but not configured — nobody asked for it yet).
- Rate limit is per-process memory — restarting the server resets everyone's quota. Fine for a
  home-LAN courtesy limiter, would need Redis or similar for a real multi-instance deployment
  (out of scope here).
