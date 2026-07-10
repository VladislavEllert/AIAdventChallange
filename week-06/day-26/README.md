# Day 26 — Local LLM up and answering

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`local_llm_smoke.py`](local_llm_smoke.py) | 3 live requests (fact / reasoning / code) to Ollama over LAN |
| [`smoke_output.log`](smoke_output.log) | Real output of the run below |
| [`../../agent-cli/tests/test_ollama_smoke.py`](../../agent-cli/tests/test_ollama_smoke.py) | pytest, skips if Ollama unreachable, real assertions otherwise |
| [`../WINDOWS_SETUP.md`](../WINDOWS_SETUP.md) | Windows-side runbook (Ollama+ComfyUI+metrics), status: done |

## Task

Local model runs, reachable via CLI/HTTP, answers ≥3 requests of different complexity.

## What was done

Windows box (RTX 4060, LAN `192.168.0.33`) already had Ollama `qwen3:4b` running and
LAN-reachable before this session (see `WINDOWS_SETUP.md`). This day is the Mac-side
verification: hit the OpenAI-compatible endpoint `http://192.168.0.33:11434/v1` for real.

3 live requests, increasing complexity:

| # | Type | Latency | Tokens |
|---|------|---------|--------|
| 1 | simple fact ("столица Франции") | 3.1s | 199 |
| 2 | reasoning (apple word problem) | 7.2s | 548 |
| 3 | code (palindrome check function) | 51.2s | 3468 |

Full transcript: [`smoke_output.log`](smoke_output.log).

**Gotcha found and fixed:** repo root has its own `.env` (Telegram bot token from week 1).
`python-dotenv`'s default `load_dotenv()` walks up from cwd and finds that root `.env`
before `agent-web/.env`, silently dropping `OLLAMA_CHAT_URL` back to `localhost`. Fixed by
loading `agent-web/.env` explicitly by path in both the smoke script and the pytest test.

**Note on latency:** the code-generation request (51s, 3468 tok) took noticeably longer per
token than the others — Qwen3 emits `<think>` reasoning tokens before the answer even
without an explicit "think step by step" instruction. Worth watching in day 29 (tuning).

Test run (live, box up, VPN off):
```
tests/test_ollama_smoke.py::test_ollama_returns_nonempty_response PASSED
tests/test_ollama_smoke.py::test_ollama_tags_lists_qwen3 PASSED
2 passed in 68.82s
```
If the Windows box is off or unreachable, the same tests skip cleanly instead of failing.

## Next

Day 27 wires this into `agent-web` itself (provider + dispatcher), plus the image path
(ComfyUI/SDXL) for the text↔image-in-one-chat flow.
