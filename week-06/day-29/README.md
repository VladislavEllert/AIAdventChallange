# Day 29 — Optimization: settings panel, resource monitoring, mobile fix

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/services/settings_store.py`](../../agent-web/agent_web/services/settings_store.py) | New settings: temperature/max_tokens/top_p/num_ctx (text) + steps/cfg/seed/size (image) |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | `_text_gen_kwargs()` — settings applied to every text completion call |
| [`agent-web/frontend/src/components/settings/SettingsPanel.tsx`](../../agent-web/frontend/src/components/settings/SettingsPanel.tsx) | Sliders panel, image section only shown for `comfyui/*` |
| [`week-06/metrics_server.py`](../metrics_server.py) | Windows-side agent: CPU/RAM/GPU/VRAM + loaded Ollama models |
| [`agent-web/agent_web/routers/metrics.py`](../../agent-web/agent_web/routers/metrics.py) | Mac-side proxy/cache for the above |
| [`agent-web/frontend/src/components/layout/MetricsHud.tsx`](../../agent-web/frontend/src/components/layout/MetricsHud.tsx) | Live HUD in the status bar |
| [`agent-web/frontend/src/hooks/useIsMobile.ts`](../../agent-web/frontend/src/hooks/useIsMobile.ts) | Mobile breakpoint hook — see below, this day also closed the mobile-adaptive gap |
| [`agent-web/frontend/src/components/layout/Sidebar.tsx`](../../agent-web/frontend/src/components/layout/Sidebar.tsx), [`RightPanel.tsx`](../../agent-web/frontend/src/components/panels/RightPanel.tsx) | Drawer/backdrop overlays on mobile instead of fixed-width flex columns |

## Task

Tune parameters (temperature/max_tokens/context), quantization, prompt template. Compare
before/after (quality, speed, resources).

**Scope, per your call earlier in this session:** quant comparison deferred — you deleted
`qwen3:8b` and don't want to download anything else right now (5GB left on the Windows SSD);
you'll pull a smaller variant later, possibly straight from a Windows session. This day covers
the settings panel + monitoring only.

## What was done

**Settings panel.** Text: temperature (0–2), max_tokens (64–4096), top_p (0–1), num_ctx
(512–16384, Ollama-only via `extra_body={"options":{"num_ctx":...}}` — verified live, works).
Image: steps, cfg, width, height, seed (with a "🎲 random" button that clears it). Applied to
every text-completion call site in `chat.py` (RAG, tool-calling, the plain path, the `/analyze`
pipeline) via one `_text_gen_kwargs()` helper — not just the happy path.

**Deliberate exception:** tool-calling's non-streaming completion call is left uncapped
(no `max_tokens` from settings applied there) — see the bug below for why.

**Resource monitoring.** `metrics_server.py` on the Windows box (stdlib `http.server` +
`psutil` + `nvidia-smi` subprocess — no FastAPI/uvicorn dependency there, kept it light on
purpose). Mac-side `/api/metrics` proxies it with a 1s cache. Frontend HUD polls every 2s,
degrades to "🖥 офлайн" if the Windows agent isn't reachable — verified both states live.

## Two real bugs found running this, not glossed over

**1. Settings max_tokens conflicts with day 28's Qwen3 finding.** Day 28 found Qwen3's
`<think>` reasoning can blow past any reasonable token cap and leave `content` empty. A
settings slider that lets you set `max_tokens=64` would silently break every Ollama response.
Didn't paper over it — bumped the default to 2048 (was going to be 1024) and put a visible
warning directly on the slider in the UI: *"Qwen3 сначала думает — низкое значение может дать
пустой ответ."* You can still set it low; you'll just see why if you do. Tool-calling's raw
completion call is deliberately left uncapped for the same reason — day 27 confirmed tool
calls work fine on Qwen3, and I didn't want to reintroduce the empty-content bug there by
routing it through the same settings cap.

**2. The metrics proxy was taking 3 full seconds per request — every one, always.** Traced it
live: `httpx.get(METRICS_URL, timeout=3.0)` against an unreachable **remote** host doesn't fail
fast like a closed localhost port does (instant RST) — the SYN just goes unanswered until the
timeout fires. Confirmed with `time curl .../api/metrics` five times in a row: exactly 3.017s,
3.018s, 3.020s... every time. With the frontend polling every 2s, requests would have piled up
indefinitely once the Windows metrics agent isn't running (which it currently isn't — you
haven't started it there yet). Fixed by dropping the timeout to 0.8s. Caught this because a
Playwright check of the HUD kept showing nothing rendered — traced it from "component doesn't
render" all the way down to "the backend request it depends on takes 3s," not just patched the
symptom.

## Mobile adaptive — folded in here (cross-cutting per the plan, but this is where it landed)

Real device check with Playwright (the honest gap flagged in day 27's README) showed the app is
**genuinely broken on a phone** — sidebar at full width, chat squeezed into ~130px, everything
overlapping. Since you explicitly asked to bring both viewports to a real, working state, fixed
it now rather than deferring further:

- `useIsMobile()` — `matchMedia('(max-width: 768px)')` hook.
- Sidebar and RightPanel render as `position: fixed` drawers with a backdrop on mobile instead
  of taking flex-row width — chat column gets the full screen.
- Sidebar defaults to open (a desktop preference, persisted) — auto-closes once on mobile
  mount so it doesn't cover the whole screen on first load.
- Top bar collapses on mobile: RAG/MCP toggles go icon-only, the 4 separate panel-shortcut
  buttons collapse into one (the panel has its own tab bar once open).
- Touch targets bumped to 44px on mobile (attach/send/stop buttons, sidebar/panel close
  buttons, panel tabs).
- Chat input font-size forced to 16px on mobile — below that, iOS Safari auto-zooms the whole
  page on focus.

Verified with real Playwright screenshots at both 390×844 and 1440×900 — sidebar drawer, right
panel drawer (including the new Settings tab), and the base chat view all confirmed rendering
correctly, not just "compiles."

## Verification

- 43/43 `agent-web` + 176/176 `agent-cli` tests green.
- New tests: `test_settings_api.py` (4), covering the PUT/GET round-trip and the
  seed-random-clear flag. `test_metrics_api.py` (3), covering reachable/unreachable/cache.
- **Test isolation bug caught and fixed along the way:** the first settings test run wrote
  real values into the live `data/settings.json` (no fixture isolation) — would have silently
  clobbered your actual running app's settings on every test run. Added an `autouse` fixture
  that monkeypatches the settings store to a `tmp_path`, and reset the real file back to sane
  defaults.
- Live end-to-end: settings PUT → real Ollama chat with `temperature=0.1` → real response,
  confirmed the value actually reaches the completion call, not just stored.
- Metrics HUD: confirmed both states live — "🖥 офлайн" when the Windows agent isn't running
  (current real state), and full gauges when a local test instance of `metrics_server.py` was
  running on the Mac (real CPU/RAM numbers, GPU/VRAM gracefully null without `nvidia-smi`).

## Honest gaps

- Quant comparison — deferred per your call, revisit once a second Qwen3 variant is downloaded
  (on Windows directly, most likely).
- `metrics_server.py` has **not** been run on the actual Windows box yet — only verified on
  the Mac (CPU/RAM real, GPU/VRAM/`nvidia-smi` code path exists but unverified against the real
  RTX 4060). `WINDOWS_SETUP.md` has the exact steps; needs you to run it there.
- No prompt-template picker (plan called this optional). Given the day's actual scope grew to
  include the mobile fix, didn't add it — flag if you want it back in scope.
