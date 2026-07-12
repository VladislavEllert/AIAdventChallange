# Day 27 — Local LLM in the app + text↔image in one chat

## Видео

[Видео дня](https://drive.google.com/drive/folders/1clLB0Q5h68tDx2e6xf_AcQwMHgRS9KW4?usp=share_link) (папка со всеми видео недели 6)

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-cli/agent_cli/llm/base.py`](../../agent-cli/agent_cli/llm/base.py) | Shared OpenAI-compatible provider base (extracted from ProxyAPIProvider) |
| [`agent-cli/agent_cli/llm/ollama.py`](../../agent-cli/agent_cli/llm/ollama.py) | `OllamaProvider` — always 0₽ |
| [`agent-cli/agent_cli/llm/dispatch.py`](../../agent-cli/agent_cli/llm/dispatch.py) | `DispatchProvider` — routes by model-id prefix (`ollama/*` → Ollama, else ProxyAPI) |
| [`agent-web/agent_web/services/comfyui_client.py`](../../agent-web/agent_web/services/comfyui_client.py) | ComfyUI image client (submit workflow, poll, fetch PNG) |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Image-model branch (SSE `image_progress`/`image`) + `client_for(model)` at the 3 tool-calling/RAG-rewrite call sites |
| [`frontend/src/components/chat/MessageBubble.tsx`](../../agent-web/frontend/src/components/chat/MessageBubble.tsx) | Renders generated image / progress bar |
| [`frontend/src/components/chat/ChatInput.tsx`](../../agent-web/frontend/src/components/chat/ChatInput.tsx) | Model picker shows 💬/🖼 type badge, placeholder swaps for image models |

## Task

App sends requests to the local LLM and shows responses, no cloud involved. Plus the
session's own extension: switch between a text model and an image model in the same
chat (Qwen writes an image prompt → switch to SDXL → picture appears in the feed).

## What was done

**Provider dispatch.** `ProxyAPIProvider` and `OllamaProvider` now share one base class
(`OpenAICompatProvider`) differing only in `base_url`/`api_key`/pricing. `DispatchProvider`
picks between them by model-id prefix and strips `ollama/` before calling Ollama (which
expects a bare tag like `qwen3:4b`). `agent-web/dependencies.py` now wires
`DispatchProvider` instead of `ProxyAPIProvider` directly — one provider object serves
every session regardless of which model each session has active.

**Model registry.** `_MODEL_PRICING` gained a `"type"` field (`text`/`image`) and two new
entries: `ollama/qwen3:4b` (0₽) and `comfyui/sdxl` (0₽, image). `GET /models` exposes
`type` so the frontend picker can badge them.

**Image path.** ComfyUI is not OpenAI-compatible — different protocol entirely (submit a
node-graph JSON, poll for completion, fetch the PNG). `comfyui_client.generate()` is a
sync generator yielding `progress`/`image`/`error` events, consumed directly inside
`chat.py`'s existing sync SSE generator. New SSE events `image_progress` and `image`
(base64 PNG, kept in-memory — not written to disk, so no `data/generated/` cleanup to
manage). When the active model's type is `image`, `chat.py` skips the RAG/tool/invariant
paths entirely — a picture isn't run through the invariant checker.

**Deliberate simplification vs. the plan:** poll `GET /history` instead of the ComfyUI
websocket. Same end-user value (a progress bar), no asyncio mixed into a sync generator.
Trade-off: progress % is time-estimate-based, not real per-step.

## Three real bugs found and fixed along the way

1. **`.env` shadowing (root cause of day 26's gotcha, worse this time).** `agent_cli/config.py`'s
   bare `load_dotenv()` uses python-dotenv's frame-based search — it resolves relative to
   `config.py`'s own file location, not the process cwd. That walks up to `agent-cli/.env`,
   which doesn't define `OLLAMA_CHAT_URL`/`COMFYUI_URL` — so those constants silently baked in
   as `localhost` at import time, even though `agent-web/.env` (found later by
   `mcp_client.py`'s own explicit load) had the right values in `os.environ`. The constant was
   already frozen wrong by then. Confirmed live: chat requests were silently hitting the Mac's
   own local Ollama (only `nomic-embed-text` installed) instead of the Windows box, failing with
   `model 'qwen3:4b' not found`. Fixed with a two-pass load: `usecwd=True` first (finds the
   running app's own `.env`), then the bare frame-based load as a fallback for repo-wide keys
   like `PROXYAPI_KEY` that only live in `agent-cli/.env`.
2. **`respond_stream_with_stats` gated on `isinstance(provider, ProxyAPIProvider)`.** With
   `DispatchProvider` now in place, that check silently failed and every chat would have fallen
   back to a non-streaming response — a real regression, not a hypothetical. Fixed to
   `hasattr(provider, "chat_stream_with_stats")`.
3. **`TokenUsageRef`/`OpenAI` patch targets.** Refactoring `ProxyAPIProvider` onto a shared base
   class would have broken `patch("agent_cli.llm.proxyapi.OpenAI", ...)` in the existing test
   suite. Kept `__init__`/`OpenAI` import in each subclass's own module (not hoisted into
   `base.py`) specifically so existing patch targets keep working — confirmed all 165
   pre-existing `agent-cli` tests still pass unchanged.

## Live verification (not mocked)

- **Ollama chat, full app path:** real SSE stream through `DispatchProvider` → Windows box,
  `"привет"` back, `cost_rub: 0.0`, real token counts.
- **ProxyAPI chat still works:** same session flow with `openai/gpt-4o-mini`, real cost > 0 —
  no regression from the dispatcher swap.
- **Tool-calling on Qwen3 via Ollama** (plan flagged this as unverified — checked live): sent
  a `tools=[...]` request to `qwen3:4b`, got back `finish_reason: 'tool_calls'` with a
  correctly-formed function call. MCP tool loop in `chat.py` works unchanged on Ollama.
- **Image generation, full app path:** real SSE stream, `comfyui/sdxl`, prompt "a red apple on
  a wooden table, photo" → real 1024×1024 PNG (embedded above the fold in the repo's test run,
  see `week-06/day-29` for the saved sample once settings/seed control lands).
- **VRAM contention, honestly measured (unplanned data point):** ran the image test back-to-back
  with a chat test that had just loaded `qwen3:4b` into Ollama. That generation took **~215s**
  end-to-end (vs. the ~44s solo benchmark from the Windows session) — bumped the client
  timeout from 180s to 240s to not falsely error out on this. Confirms the plan's risk note
  (§7): concurrent Qwen3+SDXL is real and slow on 8GB, not a hypothetical. A second run after
  Ollama's idle-unload (models unload automatically after ~5 min idle) came back to normal
  speed. Full quantified before/after belongs in day 29/30, not claimed here.

Backend: 36/36 `agent-web` tests + 176/176 `agent-cli` tests pass (was 29+165 before this day;
added dispatcher unit tests, ComfyUI client tests, image-path SSE tests, a live tool-calling
check, and fixed the two pre-existing model-price assertions that assumed everything costs
money).

## Honest gaps

- ~~Frontend viewport screenshots not captured~~ — **resolved in day 29**: Playwright got
  installed, real screenshots taken at both 390×844 and 1440×900, and mobile turned out to be
  genuinely broken (sidebar full-width, chat squeezed to ~130px). Fixed there, not here — see
  [`week-06/day-29`](../day-29/).
- Model-picker badge (💬/🖼) and placeholder swap are implemented but only unit-verified via
  TypeScript; not clicked through in a real browser session.

## Try it

Backend: `http://192.168.0.37:8765` (prod-style, if built) — dev right now:
**`http://192.168.0.37:5173/`** (Vite, proxies `/api` to the backend on :8765). Both bound to
`0.0.0.0`, reachable from your phone on the same WiFi.
