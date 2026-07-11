"""
Chat SSE streaming router.

After response:
1. check_code() — fast regex pre-check (no LLM cost)
2. check_llm()  — LLM-based thorough check (only if code check passes)
If violation → pop_last_exchange(), rollback stats, emit 'violation' event.
"""
import json
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
from agent_web.services.rag.config import TOP_K_FINAL, THRESHOLD, THRESHOLD_ANSWER
from agent_web.services.rag.task_state import extract_task_state, format_task_state_block
from agent_web.services import comfyui_client

router = APIRouter(tags=["chat"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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


@router.post("/chat/stream")
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

    def generate():
        import time
        import re as _re
        from datetime import datetime as _dt

        msg = req.message.strip()

        # ── Image model (comfyui/*) — separate protocol, not token-streamed ─
        if msg and not msg.startswith("/") and cfg.get_model_type(agent.model) == "image":
            agent.memory.add_message("user", msg)
            image_b64 = None
            try:
                for event in comfyui_client.generate(cfg.COMFYUI_URL, msg):
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
            chunk_iter_a, ref_a = agent.provider.chat_stream_with_stats(analysis_prompt, agent.model)
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
        if req.use_rag:
            _zero_usage = type("U", (), {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                "cost_rub": 0.0, "elapsed_ms": 0,
            })()
            try:
                rag_index = get_rag_index()

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
                if rag_meta["best_score"] < THRESHOLD_ANSWER:
                    not_know_msg = (
                        "I don't have information about this in the GitLab Handbook knowledge base. "
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
                rag_system_suffix = (
                    "\n\n[RAG MODE] Answer ONLY using the excerpts below. "
                    "After your answer, add a '**Sources:**' section listing the URLs used. "
                    "Include a short quote from each source that supports your answer. "
                    "If the excerpts do not contain the answer, say you don't know."
                )
                agent._try_summarize()
                messages = agent._build_messages(
                    msg, working_context=f"GitLab Handbook excerpts:\n\n{context_block}"
                )
                # Append task state + RAG instruction to system message
                messages[0] = {**messages[0], "content": messages[0]["content"] + task_state_block + rag_system_suffix}

                chunk_iter, ref = agent.provider.chat_stream_with_stats(messages, agent.model)
                full_response = ""
                for chunk in chunk_iter:
                    full_response += chunk
                    yield _sse_event("chunk", {"text": chunk})
                agent.memory.add_message("user", msg)
                agent.memory.add_message("assistant", full_response)
                usage = ref.usage
                agent.session_stats.add(usage)

            except Exception as e:
                yield _sse_event("chunk", {"text": f"\n\n_[RAG error: {e}]_"})
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
        # ─────────────────────────────────────────────────────────────────

        # ── MCP tool calling ──────────────────────────────────────────────
        tool_used = False
        usage = None

        try:
            tool_schemas = get_tools_sync() if req.use_mcp else []
        except Exception:
            tool_schemas = []

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
                    "(если пользователь не уточнил другой)."
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
                            extra_messages, agent.model
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
            chunk_iter, ref = agent.respond_stream_with_stats(req.message)
            for chunk in chunk_iter:
                yield _sse_event("chunk", {"text": chunk})
            usage = ref.usage

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

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
