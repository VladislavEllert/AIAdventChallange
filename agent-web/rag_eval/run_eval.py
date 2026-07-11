"""
RAG evaluation: run 10 questions in both modes and save comparison.

Usage:
  cd agent-web
  .venv/bin/python3 rag_eval/run_eval.py          # day22
  .venv/bin/python3 rag_eval/run_eval.py --day 23 # + filter stats + query rewrite
  .venv/bin/python3 rag_eval/run_eval.py --day 24 # + sources check + don't-know test
  .venv/bin/python3 rag_eval/run_eval.py --day 25 # + task memory multi-turn eval
"""
import sys
import json
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv

# Load root .env first (contains PROXYAPI_KEY); agent-web/.env is also loaded but lacks it
_ROOT_ENV = Path(__file__).parent.parent.parent / ".env"
if _ROOT_ENV.exists():
    load_dotenv(_ROOT_ENV)

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_web.services.rag.index import load_index
from agent_web.services.rag.retriever import search as rag_search
from agent_web.services.rag.config import INDEX_FIXED, TOP_K_FINAL, THRESHOLD, THRESHOLD_ANSWER
from agent_web.services.rag.task_state import extract_task_state, format_task_state_block
from agent_cli.llm.dispatch import DispatchProvider

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
EVAL_DIR = Path(__file__).parent

# Overridden by --model (day 28: ollama/qwen3:4b for a fully-local run).
MODEL = "openai/gpt-4o-mini"

RAG_SYSTEM = (
    "You are a helpful assistant with access to GitLab Handbook excerpts. "
    "Answer based ONLY on the provided context. "
    "After your answer, add a '**Sources:**' section with the URLs used and a short quote. "
    "If the context is insufficient, say you don't know."
)
PLAIN_SYSTEM = "You are a helpful assistant. Answer the question directly."

REWRITE_SYSTEM = (
    "Translate the user's question to English if needed, then rewrite it "
    "for semantic search over an English corpus. "
    "Expand abbreviations, add synonyms, make it more specific. "
    "Return ONLY the rewritten English query, nothing else."
)


def rewrite_query(provider: DispatchProvider, question: str) -> str:
    # Qwen3 (ollama/*) is a "thinking" model: its <think> reasoning eats the whole
    # max_tokens budget on this short rewrite task and never reaches an answer
    # (confirmed live up to max_tokens=1500, still mid-thought, no known API flag
    # reliably disables it on this Ollama build). Skip the rewrite for local models —
    # search on the raw question instead of burning 15-20s for an empty result.
    if MODEL.startswith("ollama/"):
        return question
    try:
        client, bare_model = provider.client_for(MODEL)
        resp = client.chat.completions.create(
            model=bare_model,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=80,
        )
        candidate = (resp.choices[0].message.content or "").strip()
        return candidate or question
    except Exception:
        return question


def _max_tokens_kwargs(cap: int) -> dict:
    # Qwen3 (ollama/*) is a "thinking" model — its <think> reasoning can run past
    # any capped budget (confirmed live up to 1500 tokens, still mid-thought) and
    # leaves content empty if cut off mid-reasoning. The live app's streaming path
    # already omits max_tokens for exactly this reason (works fine there). Do the
    # same here for non-streaming calls; keep the cap for cloud models (cost).
    return {} if MODEL.startswith("ollama/") else {"max_tokens": cap}


def ask_plain(provider: DispatchProvider, question: str) -> str:
    messages = [
        {"role": "system", "content": PLAIN_SYSTEM},
        {"role": "user", "content": question},
    ]
    client, bare_model = provider.client_for(MODEL)
    resp = client.chat.completions.create(
        model=bare_model, messages=messages, **_max_tokens_kwargs(400)
    )
    return (resp.choices[0].message.content or "").strip()


def ask_rag(
    provider: DispatchProvider,
    question: str,
    index,
    top_k: int,
    threshold: float,
    use_rewrite: bool = False,
) -> tuple[str, dict, str]:
    search_query = question
    if use_rewrite:
        search_query = rewrite_query(provider, question)

    hits, meta = rag_search(search_query, index, top_k=top_k, threshold=threshold)
    meta["rewritten_query"] = search_query if use_rewrite else None

    context_parts = []
    for i, (chunk, score) in enumerate(hits, 1):
        context_parts.append(
            f"[{i}] score={score:.3f} | {chunk.source} | {chunk.section}\n{chunk.text[:600]}"
        )
    context = "\n\n---\n".join(context_parts) if context_parts else "(no relevant context found)"
    messages = [
        {"role": "system", "content": RAG_SYSTEM},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    client, bare_model = provider.client_for(MODEL)
    resp = client.chat.completions.create(
        model=bare_model, messages=messages, **_max_tokens_kwargs(500)
    )
    answer = (resp.choices[0].message.content or "").strip()
    sources_used = [chunk.source for chunk, _ in hits]
    return answer, meta, search_query


SCENARIO_A = {
    "name": "New employee onboarding",
    "messages": [
        "I'm starting at GitLab next week. What should I know first?",
        "What are GitLab's core values?",
        "How does remote communication work at GitLab?",
        "What is the time-off policy? How many days do I get?",
        "Can I take parental leave?",
        "I'm a senior engineer. What's the code review process?",
        "How long should a code review typically take?",
        "What happens if I disagree with a reviewer's feedback?",
        "Is there a preference for async vs sync communication?",
        "Summarize the key things I told you I need to know as a new GitLab employee",
    ],
}

SCENARIO_B = {
    "name": "Engineering career growth",
    "messages": [
        "I'm a mid-level engineer at GitLab and I want to grow my career here. Explain GitLab's software development workflow first",
        "How are merge requests handled and reviewed?",
        "What are the engineering management principles at GitLab?",
        "How do performance reviews work for engineers?",
        "What are the criteria for promotion to senior engineer?",
        "How does GitLab handle underperforming team members?",
        "What is expected from an engineering manager vs individual contributor?",
        "How does GitLab approach psychological safety and inclusion?",
        "What mentorship or learning opportunities does GitLab offer?",
        "Based on what you've told me, what should I focus on to grow my career at GitLab?",
    ],
}

RAG_MULTI_SYSTEM = (
    "You are a helpful assistant with access to GitLab Handbook excerpts. "
    "Answer based ONLY on the provided context. "
    "After your answer, add a '**Sources:**' section listing the URLs used. "
    "If the context is insufficient, say you don't know."
)


def run_scenario(provider, index, scenario: dict) -> list[dict]:
    """Run a multi-turn scenario with task state tracking. Returns per-turn results."""
    history = []
    task_state = {"goal": "", "clarified_facts": [], "constraints": []}
    results = []

    print(f"\n  Scenario: {scenario['name']}")
    for turn_i, question in enumerate(scenario["messages"], 1):
        print(f"  Turn {turn_i}/{len(scenario['messages'])}: {question[:60]}...")

        # Rewrite query
        rewritten = rewrite_query(provider, question)

        # RAG search
        hits, meta = rag_search(rewritten, index, top_k=TOP_K_FINAL, threshold=THRESHOLD)
        meta["rewritten_query"] = rewritten

        # Extract task state (pass current history before this turn)
        task_state = extract_task_state(provider, history[-12:], task_state, model=MODEL)

        # Build context
        context_parts = []
        for i, (chunk, score) in enumerate(hits, 1):
            context_parts.append(
                f"[{i}] score={score:.3f} | {chunk.source} | {chunk.section}\n{chunk.text[:600]}"
            )
        context = "\n\n---\n".join(context_parts) if context_parts else "(no relevant context)"

        # Build messages (system + history + user)
        task_block = format_task_state_block(task_state)
        sys_content = RAG_MULTI_SYSTEM + task_block
        messages = [{"role": "system", "content": sys_content}]
        messages.extend(history[-8:])  # keep last 4 pairs
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})

        client, bare_model = provider.client_for(MODEL)
        resp = client.chat.completions.create(
            model=bare_model, messages=messages, **_max_tokens_kwargs(500)
        )
        answer = (resp.choices[0].message.content or "").strip()

        # Update history
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

        has_sources = "**Sources:**" in answer or "handbook.gitlab.com" in answer
        gate_triggered = meta["best_score"] < THRESHOLD_ANSWER

        results.append({
            "turn": turn_i,
            "question": question,
            "rewritten": rewritten,
            "answer": answer,
            "meta": meta,
            "task_state": dict(task_state),
            "has_sources": has_sources,
            "gate_triggered": gate_triggered,
        })
        src_label = "✅" if has_sources else "❌"
        print(f"    score={meta['best_score']:.3f} | sources={src_label} | goal='{task_state.get('goal', '')[:40]}'")
        time.sleep(0.3)

    return results


FILTER_THRESHOLD = 0.65  # tightened threshold for the "with filter" arm (prod default stays 0.5, see config.py)


def run_day23(provider, index, out_path):
    print("\n=== Day 23: RAG without filter vs RAG with filter (both use query rewrite) ===")
    questions = json.loads(QUESTIONS_FILE.read_text())
    rows = []

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['question'][:60]}...")

        no_filter_answer, no_filter_meta, search_q = ask_rag(
            provider, q["question"], index,
            top_k=TOP_K_FINAL, threshold=0.0, use_rewrite=True,
        )
        time.sleep(0.5)
        filtered_answer, filtered_meta, _ = ask_rag(
            provider, q["question"], index,
            top_k=TOP_K_FINAL, threshold=FILTER_THRESHOLD, use_rewrite=True,
        )
        time.sleep(0.5)

        rows.append({
            "question": q["question"],
            "expectation": q["expectation"],
            "search_query": search_q,
            "no_filter_answer": no_filter_answer,
            "no_filter_meta": no_filter_meta,
            "filtered_answer": filtered_answer,
            "filtered_meta": filtered_meta,
        })
        print(
            f"  no-filter: kept={no_filter_meta['top_k_kept']}/{no_filter_meta['top_k_raw']} "
            f"best={no_filter_meta['best_score']:.3f} | "
            f"filtered(@{FILTER_THRESHOLD}): kept={filtered_meta['top_k_kept']}/{filtered_meta['top_k_raw']} "
            f"best={filtered_meta['best_score']:.3f}"
        )

    lines = ["# RAG Evaluation — Day 23: RAG without filter vs RAG with filter\n\n"]
    lines.append(
        f"Model: `{MODEL}` | Index: fixed | top_k={TOP_K_FINAL} | query_rewrite=ON (both arms) | "
        f"no-filter threshold=0.0 | filtered threshold={FILTER_THRESHOLD}\n\n"
        "Both arms use RAG + query rewrite. The only difference: the *no-filter* arm keeps the "
        "top-K chunks by rank regardless of cosine score; the *filtered* arm drops any chunk below "
        f"{FILTER_THRESHOLD} similarity before building context.\n\n---\n\n"
    )

    for i, r in enumerate(rows, 1):
        lines.append(f"## Q{i}: {r['question']}\n\n")
        lines.append(f"**Expected:** {r['expectation']}\n\n")
        lines.append(f"**Rewritten query:** _{r['search_query']}_\n\n")

        nm = r["no_filter_meta"]
        lines.append(
            f"### RAG без фильтра (threshold=0.0)\n\n"
            f"**Stats:** raw={nm['top_k_raw']} → kept={nm['top_k_kept']} → final={nm['top_k_final']} "
            f"| best_score={nm['best_score']:.3f}\n\n"
            f"{r['no_filter_answer']}\n\n"
        )

        fm = r["filtered_meta"]
        lines.append(
            f"### RAG с фильтром (threshold={FILTER_THRESHOLD})\n\n"
            f"**Stats:** raw={fm['top_k_raw']} → kept={fm['top_k_kept']} → final={fm['top_k_final']} "
            f"| best_score={fm['best_score']:.3f}\n\n"
            f"{r['filtered_answer']}\n\n"
        )
        lines.append("---\n\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\nSaved → {out_path}")


def run_day25(provider, index, out_path):
    print("\n=== Day 25: Multi-turn RAG + Task Memory ===")
    scenario_results = []
    for scenario in [SCENARIO_A, SCENARIO_B]:
        turns = run_scenario(provider, index, scenario)
        scenario_results.append({"scenario": scenario, "turns": turns})

    lines = ["# RAG Evaluation — Day 25: Task Memory + Multi-turn\n\n"]
    lines.append(f"Model: `{MODEL}` | Index: fixed | threshold={THRESHOLD} | top_k={TOP_K_FINAL} | query_rewrite=ON\n\n---\n\n")

    for sr in scenario_results:
        s = sr["scenario"]
        turns = sr["turns"]
        sources_ok = sum(1 for t in turns if t["has_sources"])
        lines.append(f"## Scenario: {s['name']}\n\n")
        lines.append(f"**Sources present:** {sources_ok}/{len(turns)} turns ({'✅ ALL' if sources_ok == len(turns) else '⚠️ PARTIAL'})\n\n")

        goals = [t["task_state"].get("goal", "") for t in turns if t["task_state"].get("goal")]
        if goals:
            lines.append(f"**Initial goal extracted:** _{goals[0]}_\n\n")
            lines.append(f"**Final goal:** _{goals[-1]}_\n\n")

        for t in turns:
            ts = t["task_state"]
            src_label = "✅" if t["has_sources"] else "❌"
            gate_label = " [DONT-KNOW GATE]" if t["gate_triggered"] else ""
            lines.append(f"### Turn {t['turn']}: {t['question']}\n\n")
            lines.append(f"**RAG:** score={t['meta']['best_score']:.3f} | sources={src_label}{gate_label}\n\n")
            if t["rewritten"] != t["question"]:
                lines.append(f"**Rewritten:** _{t['rewritten']}_\n\n")
            if ts.get("goal"):
                lines.append(f"**Task state:**\n- Goal: {ts['goal']}\n")
                if ts.get("clarified_facts"):
                    lines.append(f"- Clarified: {'; '.join(ts['clarified_facts'][:3])}\n")
                if ts.get("constraints"):
                    lines.append(f"- Constraints: {'; '.join(ts['constraints'][:3])}\n")
                lines.append("\n")
            lines.append(f"**Answer:**\n{t['answer']}\n\n---\n\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\nSaved → {out_path}")


def main():
    global MODEL
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, default=22)
    parser.add_argument("--model", type=str, default=MODEL,
                         help="e.g. openai/gpt-4o-mini (cloud, default) or ollama/qwen3:4b (local)")
    args = parser.parse_args()
    MODEL = args.model

    index = load_index(INDEX_FIXED)
    provider = DispatchProvider()

    if args.day == 25:
        out_path = EVAL_DIR / "results_day25.md"
        run_day25(provider, index, out_path)
        return 0

    if args.day == 23:
        out_path = EVAL_DIR / "results_day23.md"
        run_day23(provider, index, out_path)
        return 0

    questions = json.loads(QUESTIONS_FILE.read_text())
    use_rewrite = args.day >= 23

    rows = []
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['question'][:60]}...")

        plain = ask_plain(provider, q["question"])
        time.sleep(0.5)
        rag_answer, meta, search_q = ask_rag(
            provider, q["question"], index,
            top_k=TOP_K_FINAL, threshold=THRESHOLD,
            use_rewrite=use_rewrite,
        )
        time.sleep(0.5)

        rows.append({
            "question": q["question"],
            "expectation": q["expectation"],
            "expected_sources": q["expected_sources"],
            "plain_answer": plain,
            "rag_answer": rag_answer,
            "rag_meta": meta,
            "search_query": search_q,
        })
        kept = meta['top_k_kept']
        total = meta['top_k_raw']
        print(f"  ✓ chunks: {meta['top_k_final']}/{total} kept | score={meta['best_score']:.3f}")
        if use_rewrite and search_q != q["question"]:
            print(f"    rewritten: {search_q[:80]}")

    # Day 24: also test "don't know" scenario
    dont_know_result = None
    if args.day >= 24:
        oob_q = "What is the current weather in Moscow today?"
        print(f"\n[DON'T KNOW TEST] {oob_q}")
        _, dk_meta, _ = ask_rag(provider, oob_q, index, top_k=TOP_K_FINAL, threshold=THRESHOLD, use_rewrite=True)
        best = dk_meta["best_score"]
        triggered = best < THRESHOLD_ANSWER
        dont_know_result = {"question": oob_q, "best_score": best, "triggered": triggered}
        print(f"  best_score={best:.3f} threshold_answer={THRESHOLD_ANSWER} → dont_know={'YES' if triggered else 'NO'}")

    # Write results markdown
    out_path = EVAL_DIR / f"results_day{args.day}.md"
    lines = [f"# RAG Evaluation — Day {args.day}\n\n"]
    lines.append(
        f"Model: `{MODEL}` | Index: fixed | threshold={THRESHOLD} | "
        f"threshold_answer={THRESHOLD_ANSWER} | top_k={TOP_K_FINAL}"
        + (" | query_rewrite=ON" if use_rewrite else "")
        + "\n\n---\n\n"
    )

    for i, r in enumerate(rows, 1):
        lines.append(f"## Q{i}: {r['question']}\n\n")
        lines.append(f"**Expected:** {r['expectation']}\n\n")
        m = r["rag_meta"]
        if args.day >= 23:
            rw = r["search_query"]
            rw_line = f" → rewritten: _{rw}_" if rw != r["question"] else ""
            lines.append(
                f"**RAG stats:** raw={m['top_k_raw']} → kept={m['top_k_kept']} → final={m['top_k_final']} "
                f"| best_score={m['best_score']:.3f}{rw_line}\n\n"
            )
        if args.day >= 24:
            has_sources = "**Sources:**" in r["rag_answer"] or "handbook.gitlab.com" in r["rag_answer"]
            lines.append(f"**Sources in answer:** {'✅' if has_sources else '❌'}\n\n")
        lines.append(f"### Without RAG\n{r['plain_answer']}\n\n")
        lines.append(f"### With RAG\n{r['rag_answer']}\n\n")
        lines.append("---\n\n")

    if dont_know_result:
        lines.append("## Don't-Know Gate Test\n\n")
        lines.append(f"**Question:** {dont_know_result['question']}\n\n")
        lines.append(f"**Best score:** {dont_know_result['best_score']:.3f} (threshold_answer={THRESHOLD_ANSWER})\n\n")
        triggered_label = '✅ YES — model says "I don\'t know"' if dont_know_result['triggered'] else '❌ NO — passed through'
        lines.append(f"**Triggered:** {triggered_label}\n\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\nSaved → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
