---
name: design-verify-loop
description: Autonomous fix-until-it-matches-the-mockup loop for UI/verstka work (describer→implementer→verifier). Use whenever building or finishing a page/component against a Figma mockup or design reference, so you don't have to click through and manually point out gaps yourself. Triggered automatically by /build when the task scope is design/verstka, not for pure logic/backend changes.
---

# design-verify-loop — describer → implementer → verifier

> Origin: mentor Arseniy Savin's advice (2026-07-17, festrider project) — see
> `.memory-bank/` or this repo's own notes for the source session if carried over.
> Problem this solves: manual pixel-fixing after "AI verstka" — repeatedly re-opening the
> page to say "here you lost the layout, here you didn't finish". This loop puts a critic
> agent in that seat instead.

## You are the ORCHESTRATOR
You do not judge the design yourself and you do not write the spec yourself. You run
describer once, then loop implementer↔design-verifier, and stop on PASS or on the
iteration cap.

## When this runs
- Manually: `/design-verify-loop "<page/component>" <figma-url-or-none>`
- Automatically from `/build`: when a build task's scope is UI/verstka against a design
  reference (see `AGENTS.md` §Exec-routing — verstka tasks route here instead of straight
  to the plain UI exec-agent).

## Steps

0. **Clarify-gate.** Confirm: which page/component, which route/URL to screenshot, and
   what design reference exists (Figma URL, PNG export, or "ask user — nothing given
   yet"). If no reference at all, stop and ask — do not guess a target to verify against.

1. **Slugify** the page/component → `<slug>`.

2. **Spawn describer once** — one `Task` call, `subagent_type: general-purpose`, prompt:
   > Read `.claude/agents/describer.md` and follow it exactly. Target: <page/component>,
   > slug <slug>. Design reference: <Figma URL, or "PNG at <path>", or "none given — ask
   > user first">.

   Describer tries Figma MCP first; if MCP fails, it will report back that it needs a
   PNG — **relay that request to the user verbatim and wait**, do not proceed with a
   guessed spec. Once it succeeds, it writes `swarm-report/<slug>-design-spec.md`.

3. **Loop, max 4 iterations:**
   a. **Implementer** — this project's UI exec-agent (e.g. `.claude/agents/frontend.md`,
      whatever this project calls it), applied directly in this session or as a `Task`
      (`general-purpose`, prompt: "Read `.claude/agents/<ui-agent>.md` and follow it.
      Implement/fix `swarm-report/<slug>-design-spec.md` for <page/component>. <On
      iterations 2+: paste the verifier's failing-items list verbatim>").
   b. **Spawn design-verifier** — one `Task` call, `subagent_type: general-purpose`,
      prompt:
      > Read `.claude/agents/design-verifier.md` and follow it exactly. Spec:
      > `swarm-report/<slug>-design-spec.md`. URL: <route>.
   c. Parse the verdict block.
      - `PASS` → stop loop, go to step 4.
      - `REWORK` → if the failing-items list is byte-identical to the previous
        iteration's list, STOP the loop early (don't burn a 4th round on a stuck fix)
        and escalate — see step 4b. Otherwise feed the failing items to the implementer
        and continue.

4. **Report to user:**
   a. On PASS: "Design verified against <spec>, <N> iteration(s), route <url>."
   b. On cap-out or stuck-repeat: list the still-failing items exactly as the verifier
      phrased them, and say plainly that this needs a manual look — do not claim done.

## Cost discipline
This loop is subagent-heavy (describer + implementer + verifier × N) — the single
biggest token-cost driver in this harness. Keep the iteration cap at 4. If the same page
needs more than 4 rounds, that's a signal the spec itself is ambiguous or the reference is
missing something — stop and ask, don't keep spending rounds on it.

## Adopting this in a new project
- Write your own UI exec-agent (`.claude/agents/<name>.md`) — this harness ships none.
- If this project has its own design-rules skill (grid, component conventions, brand
  rules), the describer and verifier should check against it — reference it by name in
  their prompts or link it from `AGENTS.md`.
- If this project has its own UI-testing skill (Playwright or otherwise), the verifier
  should use its known gotchas/mechanics rather than reinvent them.
