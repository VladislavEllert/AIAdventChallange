"""
Chat SSE streaming router.

After response:
1. check_code() — fast regex pre-check (no LLM cost)
2. check_llm()  — LLM-based thorough check (only if code check passes)
If violation → pop_last_exchange(), rollback stats, emit 'violation' event.
"""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from agent_web.dependencies import get_manager, get_rag_index
from agent_web.services.agent_manager import AgentManager
from agent_web.schemas.chat import ChatRequest
from agent_cli.invariants.store import load_invariants
from agent_cli.invariants.checker import check_code, check_llm
import agent_cli.config as cfg
from agent_web.services.mcp_client import get_tools_sync, call_tool_sync, TOOL_LABELS
from agent_web.services.rag.retriever import search as rag_search
from agent_web.services.rag.config import TOP_K_FINAL, THRESHOLD, KNOWLEDGE_BASES
from agent_web.services.rag.task_state import extract_task_state, format_task_state_block
from agent_web.services import comfyui_client
from agent_web.services.settings_store import load_settings
from agent_web.services.rate_limit import rate_limit
from agent_web.services import commands_help  # noqa: F401 — registers /help (day 31)
from agent_web.services import commands_support  # noqa: F401 — registers /support (day 33)
from agent_web.services import commands_ritual  # noqa: F401 — registers /ritual (day 35)
from agent_web.services.commands import resolve as resolve_command
from agent_web.services import tools as _fs_tools_pkg  # noqa: F401 — registers fs tools (day 34)
from agent_web.services.tools import registry as tools_registry
from agent_web.services.tools import executor as tools_executor
from agent_web.services.tools import confirm as tools_confirm

router = APIRouter(tags=["chat"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _text_gen_kwargs(model: str) -> dict:
    """Day 29: user-tunable generation params, applied to every text completion.
    num_ctx (context window) is Ollama-specific — passed via extra_body, ignored
    by ProxyAPI models."""
    s = load_settings()
    kwargs = {
        "temperature": s.get("temperature", 0.7),
        "max_tokens": s.get("max_tokens", 2048),
        "top_p": s.get("top_p", 1.0),
    }
    if model.startswith("ollama/"):
        kwargs["extra_body"] = {"options": {"num_ctx": s.get("num_ctx", 4096)}}
    return kwargs


def _load_invariant_strings() -> list[str]:
    """Load invariants from store, normalize to plain strings."""
    result: list[str] = []
    try:
        for item in load_invariants():
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.extend(str(v) for v in item.values())
    except Exception:
        pass
    return result


def _load_profile_content(profile_name: str) -> str:
    """Read profile markdown content. Returns empty string on failure."""
    try:
        path = Path(cfg.PROFILES_DIR) / f"{profile_name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


@router.post("/chat/stream", dependencies=[Depends(rate_limit)])
async def chat_stream(req: ChatRequest, manager: AgentManager = Depends(get_manager)):
    # Load fresh invariants on every request (user may have added via InvariantsPanel)
    invariants = _load_invariant_strings()

    # Load profile content
    profile_content = _load_profile_content(req.profile_name) if req.profile_name else ""

    # Get or create agent, applying current request params
    agent = manager.get_or_create(
        req.session_id,
        persona=req.persona or "",
        model=req.model or "",
        profile_content=profile_content,
    )

    # Always sync fresh invariants + profile into existing agent instance
    agent.invariants = invariants
    if profile_content:
        agent.profile_content = profile_content
    if req.model:
        agent.model = req.model

    def _generate_core(stream_id: str):
        import time
        import re as _re
        from datetime import datetime as _dt

        msg = req.message.strip()

        # ── Image model (comfyui/*) — separate protocol, not token-streamed ─
        if msg and not msg.startswith("/") and cfg.get_model_type(agent.model) == "image":
            agent.memory.add_message("user", msg)
            image_b64 = None
            s = load_settings()
            try:
                for event in comfyui_client.generate(
                    cfg.COMFYUI_URL, msg,
                    seed=s.get("image_seed"),
                    steps=s.get("image_steps", 20),
                    cfg=s.get("image_cfg", 8.0),
                    width=s.get("image_width", 1024),
                    height=s.get("image_height", 1024),
                ):
                    if event["type"] == "progress":
                        yield _sse_event("image_progress", {"pct": event["pct"]})
                    elif event["type"] == "image":
                        image_b64 = event["data_b64"]
                        yield _sse_event("image", {"data_b64": image_b64})
                    elif event["type"] == "error":
                        yield _sse_event("chunk", {"text": f"❌ {event['message']}"})
            except Exception as e:
                yield _sse_event("chunk", {"text": f"❌ ComfyUI error: {e}"})
            agent.memory.add_message("assistant", "[generated image]" if image_b64 else "[generation failed]")
            yield _sse_event("usage", {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                "cost_rub": 0.0, "elapsed_ms": 0,
            })
            manager.save(req.session_id)
            yield _sse_event("done", {})
            return
        # ─────────────────────────────────────────────────────────────────

        # ── New slash-command registry (day 31+: /help, later /support, /ritual) ──
        # Checked BEFORE the legacy hardcoded commands below — none of those are
        # migrated here (see services/commands.py docstring).
        _cmd = resolve_command(msg)
        if _cmd:
            # stream_id passed through for day-35's /ritual (needs it for the
            # git_commit confirm handshake, same stream_id chat.py's own tool
            # loop uses — reuses the SAME staleness detection, see confirm.py).
            # /help and /support ignore the kwarg (**_kw catch-all).
            for _event, _data in _cmd.handler(msg, req, agent, manager, stream_id=stream_id):
                yield _sse_event(_event, _data)
            return
        # ─────────────────────────────────────────────────────────────────

        # ── /mcp — list available tools ───────────────────────────────────
        if msg.lower() in ("/mcp", "/mcp tools", "/mcp list"):
            try:
                from agent_web.services.mcp_client import MCP_SERVERS, _tool_registry
                tools = get_tools_sync()
                lines = ["**🔧 MCP Tools** (2 сервера)\n\n"]
                # Group by server
                by_server: dict[str, list] = {}
                for t in tools:
                    sname = _tool_registry.get(t["function"]["name"], "?")
                    by_server.setdefault(sname, []).append(t)
                server_labels = {
                    "finance": f"🖥️ VPS Finance ({MCP_SERVERS.get('finance', '')})",
                    "github":  f"🐙 GitHub MCP ({MCP_SERVERS.get('github', '')})",
                }
                for sname, stools in by_server.items():
                    lines.append(f"\n**{server_labels.get(sname, sname)}**\n")
                    for t in stools:
                        fn = t["function"]
                        desc = fn["description"].split(".")[0]
                        lines.append(f"• `{fn['name']}` — {desc}\n")
                lines.append(f"\nВсего инструментов: {len(tools)}")
                yield _sse_event("chunk", {"text": "".join(lines)})
            except Exception as e:
                yield _sse_event("chunk", {"text": f"❌ MCP недоступен: {e}"})
            yield _sse_event("done", {})
            return

        # ── /history TICKER [minutes] — aggregated history from SQLite ──────
        if msg.lower().startswith("/history"):
            parts = msg.split()
            ticker = parts[1].upper() if len(parts) > 1 else "IMOEX"
            minutes = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 60
            try:
                result = call_tool_sync("get_moex_history", {"ticker": ticker, "minutes": minutes})
                yield _sse_event("chunk", {"text": f"📈 **История {ticker}**\n\n{result}"})
            except Exception as e:
                yield _sse_event("chunk", {"text": f"❌ Ошибка: {e}"})
            yield _sse_event("done", {})
            return

        # ── /ping TICKER [interval] — live price stream ───────────────────
        if msg.lower().startswith("/ping"):
            parts = msg.split()
            ticker = parts[1].upper() if len(parts) > 1 else "IMOEX"
            interval = max(1, int(parts[2])) if len(parts) > 2 and parts[2].isdigit() else 5
            count = 10

            # Detect index vs stock
            is_index = ticker in ("IMOEX", "RTSI", "MICEXINDEXCF")
            tool_name = "get_moex_index" if is_index else "get_moex_quote"
            unit = "пунктов" if is_index else "RUB"

            yield _sse_event("chunk", {
                "text": f"📡 **{ticker}** — мониторинг каждые {interval}с ({count} замеров)\n\n```\n"
            })

            start_val = None
            all_values: list[float] = []

            for i in range(count):
                ts = _dt.now().strftime("%H:%M:%S")
                try:
                    raw = call_tool_sync(tool_name, {"ticker": ticker})
                    # extract first float from response
                    nums = _re.findall(r"\d+[\.,]\d+", raw)
                    val = float(nums[0].replace(",", ".")) if nums else None
                except Exception as exc:
                    raw, val = f"ошибка: {exc}", None

                if val is not None:
                    all_values.append(val)
                    if start_val is None:
                        start_val = val
                    delta = ((val - start_val) / start_val * 100) if start_val else 0
                    sign = "▲" if delta >= 0 else "▼"
                    line = f"{ts}  {ticker:<8}  {val:>10.2f} {unit}  {sign}{abs(delta):.2f}%\n"
                else:
                    line = f"{ts}  {raw}\n"

                yield _sse_event("chunk", {"text": line})

                if i < count - 1:
                    time.sleep(interval)

            # Summary
            if all_values and start_val:
                end_val = all_values[-1]
                total = ((end_val - start_val) / start_val * 100)
                sign = "▲" if total >= 0 else "▼"
                yield _sse_event("chunk", {"text": (
                    f"```\n\n📊 **Итог**: {start_val:.2f} → {end_val:.2f}  "
                    f"{sign} {total:+.2f}%  "
                    f"мин {min(all_values):.2f} / макс {max(all_values):.2f}"
                )})
            else:
                yield _sse_event("chunk", {"text": "```"})

            yield _sse_event("done", {})
            return
        # ── /analyze SYMBOL [interval] — guaranteed 3-step crypto pipeline ──
        if msg.lower().startswith("/analyze"):
            parts = msg.split()
            symbol = parts[1].upper() if len(parts) > 1 else "BTCUSDT"
            interval = parts[2] if len(parts) > 2 else "1h"
            filename = f"{symbol.lower()}_{interval}_analysis.md"

            yield _sse_event("chunk", {"text": f"🔬 **Анализ {symbol}** (интервал {interval})\n\n"})

            # Step 1: fetch klines
            yield _sse_event("tool_start", {"name": "get_crypto_klines", "label": "📊 Загружаю свечи Binance..."})
            try:
                klines_json = call_tool_sync("get_crypto_klines", {"symbol": symbol, "interval": interval, "limit": 50})
            except Exception as e:
                klines_json = ""
                yield _sse_event("chunk", {"text": f"❌ Ошибка загрузки свечей: {e}\n"})
            yield _sse_event("tool_done", {"name": "get_crypto_klines", "result_preview": klines_json[:80]})

            if not klines_json or klines_json.startswith("Error") or klines_json.startswith("Binance"):
                yield _sse_event("chunk", {"text": f"❌ {klines_json}"})
                yield _sse_event("done", {})
                return

            # Step 2: calculate indicators
            yield _sse_event("tool_start", {"name": "calculate_indicators", "label": "🧮 Считаю RSI/MACD..."})
            try:
                indicators = call_tool_sync("calculate_indicators", {"klines_json": klines_json})
            except Exception as e:
                indicators = f"Ошибка расчёта: {e}"
            yield _sse_event("tool_done", {"name": "calculate_indicators", "result_preview": indicators[:80]})

            # Step 3: LLM generates report text
            analysis_prompt = agent._build_messages(
                f"Ты — финансовый аналитик. Вот технический анализ {symbol} (интервал {interval}):\n\n"
                f"{indicators}\n\n"
                f"Напиши краткий торговый отчёт: что означают эти показатели, "
                f"какой сигнал (BUY/SELL/HOLD) и почему. 3-5 предложений."
            )
            report_text = ""
            chunk_iter_a, ref_a = agent.provider.chat_stream_with_stats(
                analysis_prompt, agent.model, **_text_gen_kwargs(agent.model)
            )
            for chunk in chunk_iter_a:
                report_text += chunk
                yield _sse_event("chunk", {"text": chunk})
            usage = ref_a.usage
            agent.session_stats.add(usage)

            # Step 4: save report
            full_report = f"# {symbol} Анализ ({interval})\n\n{indicators}\n\n## Вывод\n\n{report_text}"
            yield _sse_event("tool_start", {"name": "save_report", "label": "💾 Сохраняю отчёт..."})
            try:
                save_result = call_tool_sync("save_report", {"filename": filename, "content": full_report})
            except Exception as e:
                save_result = f"Ошибка сохранения: {e}"
            yield _sse_event("tool_done", {"name": "save_report", "result_preview": save_result[:80]})

            yield _sse_event("chunk", {"text": f"\n\n---\n_{save_result}_"})

            agent.memory.add_message("user", req.message)
            agent.memory.add_message("assistant", report_text)

            yield _sse_event("usage", {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_rub": round(usage.cost_rub, 6),
                "elapsed_ms": usage.elapsed_ms,
            })
            yield _sse_event("done", {})
            return
        # ─────────────────────────────────────────────────────────────────

        # ── RAG path (days 22–24) ─────────────────────────────────────────
        # Day 34 (34.1): this branch used to `return` unconditionally after
        # streaming, so the tool-calling loop below (which the file-agent
        # tools need) was UNREACHABLE whenever RAG was also on. Fix: when
        # tools are requested too (req.use_mcp), collect the RAG excerpts into
        # rag_context_block/rag_label/rag_task_state_block and fall through —
        # the tool-calling section injects them into the system message before
        # the tool loop runs. The original fast path (`use_rag and not
        # use_mcp`) still returns immediately, unchanged, right after
        # streaming — this keeps regression risk to pure-RAG-chat callers
        # (ragEnabled toggle with MCP off) at zero.
        rag_context_block: str | None = None
        rag_label: str = ""
        rag_task_state_block: str = ""
        if req.use_rag:
            _zero_usage = type("U", (), {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                "cost_rub": 0.0, "elapsed_ms": 0,
            })()
            try:
                _handbook_cfg = KNOWLEDGE_BASES["handbook"]
                rag_index = get_rag_index(kb="handbook")

                # Day 23: query rewrite — short LLM call to expand/clarify query
                rewritten_query = msg
                # Qwen3 (ollama/*) is a "thinking" model: its <think> reasoning eats the
                # whole max_tokens budget on this short rewrite task and never reaches an
                # answer (confirmed live up to max_tokens=1500, still mid-thought) — no
                # known API flag reliably disables it on this Ollama build. Skip the
                # rewrite for local models rather than burn 15-20s for an empty result.
                if not agent.model.startswith("ollama/"):
                    try:
                        rw_client, rw_model = agent.provider.client_for(agent.model)
                        rw_resp = rw_client.chat.completions.create(
                            model=rw_model,
                            messages=[
                                {"role": "system", "content": (
                                    "Translate the user's question to English if needed, then rewrite it "
                                    "for semantic search over an English corpus. "
                                    "Expand abbreviations, add synonyms, make it more specific. "
                                    "Return ONLY the rewritten English query, nothing else."
                                )},
                                {"role": "user", "content": msg},
                            ],
                            max_tokens=80,
                        )
                        candidate = (rw_resp.choices[0].message.content or "").strip()
                        if candidate:
                            rewritten_query = candidate
                    except Exception:
                        pass  # fallback to original msg already set above

                # Day 25: extract/update task state from conversation history
                task_state = extract_task_state(
                    agent.provider,
                    agent.memory.short_term[-12:],
                    agent.memory.working or {},
                    model=agent.model,
                )
                agent.memory.working = task_state

                hits, rag_meta = rag_search(
                    rewritten_query, rag_index, top_k=TOP_K_FINAL, threshold=THRESHOLD
                )
                rag_meta["rewritten_query"] = rewritten_query

                # Day 24: "don't know" gate — if best score below answer threshold
                if rag_meta["best_score"] < _handbook_cfg["threshold_answer"]:
                    not_know_msg = (
                        f"I don't have information about this in the {_handbook_cfg['label']} knowledge base. "
                        "Could you rephrase or ask something more specific?"
                    )
                    if rag_meta["best_score"] > 0:
                        # Suggest the closest section found
                        closest = rag_search(rewritten_query, rag_index, top_k=1, threshold=0.0)[0]
                        if closest:
                            top_chunk, top_score = closest[0]
                            not_know_msg += (
                                f"\n\nClosest topic found (score={top_score:.3f}): "
                                f"**{top_chunk.section}** — {top_chunk.source}"
                            )
                    agent.memory.add_message("user", msg)
                    agent.memory.add_message("assistant", not_know_msg)
                    yield _sse_event("chunk", {"text": not_know_msg})
                    yield _sse_event("rag_meta", rag_meta)
                    yield _sse_event("task_state", task_state)
                    yield _sse_event("sources", [])
                    yield _sse_event("usage", {
                        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                        "cost_rub": 0.0, "elapsed_ms": 0,
                    })
                    manager.save(req.session_id)
                    yield _sse_event("done", {})
                    return

                # Day 24: emit sources SSE right after retrieval (before LLM response)
                sources_payload = [
                    {
                        "source": chunk.source,
                        "section": chunk.section,
                        "chunk_id": chunk.chunk_id,
                        "quote": chunk.text[:300],
                        "score": round(score, 4),
                    }
                    for chunk, score in hits
                ]
                yield _sse_event("sources", sources_payload)
                yield _sse_event("rag_meta", rag_meta)
                yield _sse_event("task_state", task_state)

                # Build context with numbered excerpts
                context_parts = []
                for i, (chunk, score) in enumerate(hits, 1):
                    context_parts.append(
                        f"[{i}] score={score:.3f} | {chunk.source} | {chunk.section}\n{chunk.text[:700]}"
                    )
                context_block = "\n\n---\n".join(context_parts)

                # Day 25: task state injection + Day 24: citation instruction
                task_state_block = format_task_state_block(task_state)

                if not req.use_mcp:
                    # ── Fast path (unchanged from days 22-24): RAG on, tools
                    # off — stream the RAG answer directly, no tool loop. ──
                    rag_system_suffix = (
                        "\n\n[RAG MODE] Answer ONLY using the excerpts below. "
                        "After your answer, add a '**Sources:**' section listing the URLs used. "
                        "Include a short quote from each source that supports your answer. "
                        "If the excerpts do not contain the answer, say you don't know."
                    )
                    agent._try_summarize()
                    messages = agent._build_messages(
                        msg, working_context=f"{_handbook_cfg['label']} excerpts:\n\n{context_block}"
                    )
                    # Append task state + RAG instruction to system message
                    messages[0] = {**messages[0], "content": messages[0]["content"] + task_state_block + rag_system_suffix}

                    chunk_iter, ref = agent.provider.chat_stream_with_stats(
                        messages, agent.model, **_text_gen_kwargs(agent.model)
                    )
                    full_response = ""
                    for chunk in chunk_iter:
                        full_response += chunk
                        yield _sse_event("chunk", {"text": chunk})
                    agent.memory.add_message("user", msg)
                    agent.memory.add_message("assistant", full_response)
                    usage = ref.usage
                    agent.session_stats.add(usage)

                    yield _sse_event("usage", {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                        "cost_rub": round(usage.cost_rub, 6),
                        "elapsed_ms": usage.elapsed_ms,
                    })
                    manager.save(req.session_id)
                    yield _sse_event("done", {})
                    return
                # else: tools requested too (day 34) — DON'T return. Stash the
                # RAG excerpts; the tool-calling section below injects them
                # into the system message before its tool loop runs.
                rag_context_block = context_block
                rag_label = _handbook_cfg["label"]
                rag_task_state_block = task_state_block

            except Exception as e:
                yield _sse_event("chunk", {"text": f"\n\n_[RAG error: {e}]_"})
                if not req.use_mcp:
                    usage = _zero_usage
                    yield _sse_event("usage", {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                        "cost_rub": round(usage.cost_rub, 6),
                        "elapsed_ms": usage.elapsed_ms,
                    })
                    manager.save(req.session_id)
                    yield _sse_event("done", {})
                    return
                # else: degrade gracefully — proceed to the tool loop below
                # without RAG context rather than terminating the turn.
        # ─────────────────────────────────────────────────────────────────

        # ── MCP tool calling (+ day 34 local file-agent tools) ─────────────
        tool_used = False
        usage = None

        try:
            mcp_schemas = get_tools_sync() if req.use_mcp else []
        except Exception:
            mcp_schemas = []
        local_schemas = tools_registry.get_schemas() if req.use_mcp else []
        tool_schemas = mcp_schemas + local_schemas

        if tool_schemas:
            try:
                agent._try_summarize()
                all_messages = agent._build_messages(req.message)

                # Always inject current datetime — never let model guess the date
                try:
                    current_dt = call_tool_sync("get_current_datetime", {})
                except Exception:
                    current_dt = None

                tool_names = [t["function"]["name"] for t in tool_schemas
                              if t["function"]["name"] != "get_current_datetime"]
                hint_parts = []
                if current_dt:
                    hint_parts.append(f"\n\n[СИСТЕМНЫЙ ФАКТ] Текущая дата и время: {current_dt}")
                hint_parts.append(
                    f"\nДОСТУПНЫЕ ИНСТРУМЕНТЫ: {', '.join(tool_names)}.\n"
                    "Используй web_search когда: пользователь просит найти в интернете, "
                    "спрашивает о новостях/релизах/ценах/событиях после августа 2025, "
                    "или когда не уверен в актуальности факта. "
                    "Не отвечай из памяти по фактам которые могли измениться.\n"
                    "Используй issue_write когда: пользователь просит создать issue/задачу в GitHub. "
                    "Для issue_write обязательно передай: method='create', owner (владелец репо), repo (имя репо), "
                    "title (заголовок), body (описание). "
                    "Репозиторий пользователя по умолчанию: owner='VladislavEllert', repo='AIAdventChallange' "
                    "(если пользователь не уточнил другой).\n"
                    "Используй search_files/read_file/list_dir когда пользователь просит найти "
                    "места использования чего-то в коде, изучить файл(ы) или содержимое директории "
                    "этого репозитория. Для 'найди все места X и приведи к одному виду' — сначала "
                    "search_files, затем read_file на каждом найденном месте (можно несколько раз), "
                    "затем сформулируй ответ как unified diff. "
                    "write_file/delete_file — ОПАСНЫЕ операции, требуют подтверждения человеком: "
                    "используй только когда пользователь явно просит изменить или удалить файл; "
                    "для write_file передавай dry_run=false, иначе запись не применится."
                )
                # Day 34: fold the RAG excerpts (if the RAG toggle was also on for
                # this turn — see the control-flow fix above) into the same system
                # message the tool loop uses, instead of losing them to the RAG
                # branch's old unconditional `return`.
                if rag_context_block:
                    hint_parts.append(
                        f"\n\n[RAG CONTEXT — {rag_label}]\n{rag_context_block}" + rag_task_state_block
                    )
                hint = "".join(hint_parts)
                all_messages[0] = {**all_messages[0], "content": all_messages[0]["content"] + hint}

                # Remove get_current_datetime from tool_schemas — handled above
                tool_schemas_for_llm = [t for t in tool_schemas
                                        if t["function"]["name"] != "get_current_datetime"]
                tc_client, tc_model = agent.provider.client_for(agent.model)
                tool_response = tc_client.chat.completions.create(
                    model=tc_model,
                    messages=all_messages,
                    tools=tool_schemas_for_llm or None,
                    tool_choice="auto" if tool_schemas_for_llm else "none",
                )
                choice = tool_response.choices[0]

                # ── Multi-step tool loop (max MAX_TOOL_ROUNDS iterations) ──
                MAX_TOOL_ROUNDS = 6
                tool_used = True
                extra_messages = list(all_messages)

                for _round in range(MAX_TOOL_ROUNDS):
                    if _round == 0:
                        # Reuse the already-made first call
                        cur_choice = choice
                    else:
                        tool_resp_n = tc_client.chat.completions.create(
                            model=tc_model,
                            messages=extra_messages,
                            tools=tool_schemas_for_llm or None,
                            tool_choice="auto" if tool_schemas_for_llm else "none",
                        )
                        cur_choice = tool_resp_n.choices[0]

                    if cur_choice.finish_reason != "tool_calls" or not cur_choice.message.tool_calls:
                        # LLM has final answer — stream it
                        chunk_iter_f, ref_f = agent.provider.chat_stream_with_stats(
                            extra_messages, agent.model, **_text_gen_kwargs(agent.model)
                        )
                        full_response = ""
                        for chunk in chunk_iter_f:
                            full_response += chunk
                            yield _sse_event("chunk", {"text": chunk})
                        agent.memory.add_message("user", req.message)
                        agent.memory.add_message("assistant", full_response)
                        usage = ref_f.usage
                        agent.session_stats.add(usage)
                        break

                    # Execute all tool calls in this round
                    extra_messages.append({
                        "role": "assistant",
                        "content": cur_choice.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in cur_choice.message.tool_calls
                        ],
                    })

                    for tc in cur_choice.message.tool_calls:
                        tc_name = tc.function.name
                        tc_args = json.loads(tc.function.arguments or "{}")
                        tc_label = TOOL_LABELS.get(tc_name, f"⚙️ {tc_name}...")

                        yield _sse_event("tool_start", {"name": tc_name, "label": tc_label})

                        if tools_registry.get(tc_name) is not None:
                            # Day 34: local file-agent tool — routed through the
                            # danger/confirm gate instead of call_tool_sync (MCP).
                            # execute_stream() never raises (see tools/executor.py).
                            tc_result = None
                            for _kind, _payload in tools_executor.execute_stream(
                                tc_name, tc_args, stream_id=stream_id,
                            ):
                                if _kind == "confirm_request":
                                    yield _sse_event("confirm_request", _payload)
                                elif _kind == "keepalive":
                                    yield ": keepalive\n\n"
                                elif _kind == "confirm_result":
                                    yield _sse_event("confirm_result", _payload)
                                elif _kind == "tool_result":
                                    tc_result = _payload["result"]
                            if tc_result is None:
                                tc_result = "Tool error: no result produced."
                        else:
                            try:
                                tc_result = call_tool_sync(tc_name, tc_args)
                            except Exception as e:
                                tc_result = f"Tool error: {e}"

                        yield _sse_event("tool_done", {"name": tc_name, "result_preview": tc_result[:100]})

                        extra_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tc_result,
                        })
                    # Continue loop — LLM will see results and decide next step
            except Exception:
                # Tools failed — fall through to normal response
                tool_used = False
        # ─────────────────────────────────────────────────────────────────

        if not tool_used:
            try:
                chunk_iter, ref = agent.respond_stream_with_stats(
                    req.message, **_text_gen_kwargs(agent.model)
                )
                got_any_chunk = False
                for chunk in chunk_iter:
                    got_any_chunk = True
                    yield _sse_event("chunk", {"text": chunk})
                usage = ref.usage
                if not got_any_chunk:
                    # Stream "succeeded" but produced nothing — e.g. Qwen3's
                    # <think> ate the whole token budget (day 28 finding).
                    # Show something rather than a silently empty bubble.
                    yield _sse_event("chunk", {"text": "⚠️ Модель не вернула ответ (пустой content — возможно, не уложилась в лимит токенов на размышление)."})
            except Exception as e:
                # Model unreachable/timed out/errored — this used to fail
                # silently: no chunk, no error, the assistant bubble just sat
                # there empty forever. Surface it instead.
                yield _sse_event("chunk", {"text": f"❌ Не удалось получить ответ от модели `{agent.model}`: {e}"})
                yield _sse_event("usage", {
                    "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                    "cost_rub": 0.0, "elapsed_ms": 0,
                })
                manager.save(req.session_id)
                yield _sse_event("done", {})
                return

        # ── Invariant check ───────────────────────────────────────────────
        if invariants:
            # Get the response that was just added to memory
            response_text = (
                agent.memory.short_term[-1]["content"]
                if agent.memory.short_term and agent.memory.short_term[-1]["role"] == "assistant"
                else ""
            )

            ok, violation_desc = check_code(response_text, invariants)
            if ok:
                # Deeper LLM check (synchronous — runs in Starlette thread pool)
                ok, violation_desc = check_llm(
                    response_text, invariants, manager.provider, agent.model
                )

            if not ok:
                # Rollback: remove last exchange from memory
                agent.memory.pop_last_exchange()
                # Rollback stats
                agent.session_stats.cost_rub -= usage.cost_rub
                agent.session_stats.prompt_tokens -= usage.prompt_tokens
                agent.session_stats.completion_tokens -= usage.completion_tokens
                agent.session_stats.calls = max(0, agent.session_stats.calls - 1)

                yield _sse_event("violation", {
                    "invariant": violation_desc,
                    "description": violation_desc,
                })
                yield _sse_event("done", {})
                return
        # ─────────────────────────────────────────────────────────────────

        yield _sse_event("usage", {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_rub": round(usage.cost_rub, 6),
            "elapsed_ms": usage.elapsed_ms,
        })

        manager.save(req.session_id)
        yield _sse_event("done", {})

    def generate():
        # Day 34: a "stream session" — NOT req.session_id (which persists across many
        # messages) — scoped to this single SSE request/response. A confirm POST for a
        # call_id belonging to an already-ended stream (closed/stale tab) is auto-denied
        # by tools/confirm.py; see that module's docstring.
        stream_id = uuid.uuid4().hex
        tools_confirm.start_session(stream_id)
        try:
            yield from _generate_core(stream_id)
        finally:
            tools_confirm.end_session(stream_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
