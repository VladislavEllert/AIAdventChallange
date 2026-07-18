---
name: review
description: Review a finished change against its plan. Spawns 1 reviewer subagent, reports ship/rework with severity-tagged findings. Use AFTER /build.
---

# Skill: /review

ORCHESTRATOR. One reviewer subagent. Read-only — the reviewer does not fix.

## Invocation
`/review <slug>`

## Steps
1. **Gather**: plan `swarm-report/<slug>-plan.md` + build report `swarm-report/<slug>-build.md`
   + the diff. **Scope the diff to the plan's own files** — `git diff -- <file1> <file2> ...`
   listing exactly the plan's `affected_files` (plus any new untracked files the build report
   names), NEVER a bare `git diff`/`git diff HEAD`. A bare diff picks up whatever else is
   sitting unstaged in the working tree, including another session's in-flight work on a
   shared file (e.g. `cms/src/index.ts` touched by two plans at once) — the reviewer then
   flags the other session's hunks as scope creep in THIS review, which is noise, not signal
   (found 14.07, photo-management-hub-cover: raw `git diff` pulled in an unrelated parallel
   build's changes to the same file). For untracked new files, diff each explicitly
   (`git diff --no-index /dev/null <file>`) and append to the same diff text.
2. **Before spawning: re-read the diff text you're about to send.** Confirm it is non-empty
   and actually contains the feature's changes, not just the prompt scaffolding — an empty or
   missing diff paste wastes a full round-trip (found 14.07, same session: first reviewer spawn
   forgot to paste the diff and had to be re-launched).
3. **Spawn 1 reviewer** (`Task`, `general-purpose`). Prompt:
   > Answer TERSE. Read `.claude/agents/reviewer.md` and follow it exactly.
   > Plan: swarm-report/<slug>-plan.md
   > Diff below:
   > <paste git diff here>

   Paste the diff INTO the prompt — the reviewer must not re-read the whole repo.
4. **Verify the findings are actually itemized.** If `verdict: rework` but `findings` is
   empty or missing entries, do NOT report that as-is — resume the same reviewer agent
   (`SendMessage` to its `agentId`) and demand the concrete per-finding list
   (`path:line — SEVERITY: problem. fix.`) before reporting anything to the user. A
   rework verdict with no findings gives the user nothing actionable.
5. **Report** the reviewer's verdict + findings verbatim.
6. If `verdict: rework` — the findings ARE the input to a `/build <slug>` retry. Do not
   auto-fix here; hand them back and let the user decide.
