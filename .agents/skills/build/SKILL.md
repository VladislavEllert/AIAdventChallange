---
name: build
description: Implement an already-approved plan from swarm-report/<slug>-plan.md. Routes each task to the executing agent that owns its file scope, runs the tests, writes an implementation report. Use AFTER /plan, never before.
---

# Skill: /build

ORCHESTRATOR. You route work to executing agents by file scope. No code edits in the
main loop.

## Invocation
`/build <slug>`

## Steps
1. **Find the plan**: `swarm-report/<slug>-plan.md`. Missing → abort:
   "Run `/plan \"<feature>\"` first."
2. **Check Blockers** in the plan. Any unresolved HIGH → abort and name it. The user must
   resolve or explicitly waive it.
3. **Route by scope**: read the plan's `affected_files`. Match each against this project's
   own Executing table (in `AGENTS.md` — one row per exec-agent this project defines, e.g.
   a frontend agent, a backend agent). This harness ships no stack-specific exec-agents —
   write your own `.claude/agents/<scope>.md` per project and list them in `AGENTS.md`.
   Group files by agent. No match for a file (infra config, build tooling) → ask the user
   which agent owns it.
   **Exception — design/verstka scope**: if the task is building or finishing UI against a
   Figma mockup or other design reference (not pure logic/backend), do NOT spawn the plain
   UI exec-agent directly — invoke the `design-verify-loop` skill instead. It runs
   describer→implementer(your UI exec-agent)→verifier autonomously until the result matches
   the reference, instead of a human manually click-checking afterward.
4. **Spawn the matched exec agents** — one `Task` call each, in parallel when a feature
   spans several layers (single message, N calls, `subagent_type: general-purpose`).
   Prompt each:
   > Answer TERSE. Read `.claude/agents/<scope>.md` and follow it exactly.
   > Plan: swarm-report/<slug>-plan.md. Your scope: <the files for this agent>.
   If one agent's output changes a contract another needs, pass that note into the
   dependent agent's prompt — or run the producing agent first, then the consumer.
5. **Verify**: read each agent's `tests_result`. Any `status: blocked` or failing test →
   do NOT claim success. Report the failures verbatim and stop. Offer `/build <slug>`
   retry after the fix.
5b. **Live check — mandatory when scope touches any user-facing UI.** Passing unit/
   component tests with mocked dependencies is NOT evidence the feature works — it only
   proves the mocked logic runs. Before writing the build report: invoke this project's
   UI-testing skill (if it has one), or drive the running app yourself — click the actual
   golden path and at least one edge case — and note what you observed. If you genuinely
   cannot reach a live instance, say so explicitly in the build report ("not manually
   verified — no live instance reachable") instead of silently skipping this step.
6. **Write** `swarm-report/<slug>-build.md`: per-agent changed files, test commands +
   real results, cross-layer notes, and the live-check outcome from step 5b (what was
   clicked, what was seen, or why it wasn't possible).
7. **Report** to user: status per scope + test results. Quote real output — no "done"
   without proof. For UI-touching builds, "done" requires 5b, not just green tests.
8. **Plan text vs. a better reference found mid-build — update the plan file immediately,
   same session.** If live work proves an explicit plan line wrong (a stale acceptance
   criterion written before the real reference arrived), edit the plan's text right then —
   don't leave it stale for `/review` to flag as a false "rework" later.
9. **A build-time / containerized environment is not the same claim as a host-side dev
   run.** If any acceptance criterion depends on how the actual deploy/build pipeline
   behaves (build-time env vars, an isolated network namespace, a fresh-container
   assumption), verify it through that real pipeline at least once before calling the
   build stage done — not a host-side equivalent that happens to share resources the real
   build won't have.
