---
name: skill-creator
description: Build new skills for this project. Use when a repeating pattern, stack-specific convention, or workflow needs to be captured as a reusable skill. Keeps skills narrow and avoids bloating context.
---

# skill-creator — building your own skills

> Core rule: **don't bloat context.** A skill only earns its place if it saves more than it
> costs.

## When to create a skill

✅ Create one if:
- A pattern repeats (3+ times) and is easy to describe as rules.
- There's project-specific knowledge the agent would otherwise guess wrong.
- A workflow has clear steps (testing, release, review).

❌ Don't create one if:
- It's a one-off task.
- It's already covered by an existing skill or `AGENTS.md`/`CLAUDE.md`.
- "Just in case" — that's noise, not signal.

## Skill structure

```
.claude/skills/<name>/SKILL.md
```

Frontmatter:
```yaml
---
name: kebab-case-name
description: <one line — WHEN to use it and WHAT it gives. This is what decides whether the model picks it up. Be specific.>
---
```

Body: only what's actually needed while working. No filler.

## Quality rules

1. **`description` decides everything** — it loads into context always. It must clearly
   state the trigger. Vague = the skill won't fire, or fires at the wrong time.
2. **Body loads on demand** — put details, checklists, examples there. Keep it focused.
3. **One skill, one topic.** Don't cram design + testing + git into one file.
4. **Link, don't duplicate.** Overlaps with another skill/doc → link to it, don't copy
   (DRY).
5. **Narrow to this project's actual stack.** Concrete tech names and file paths, not
   abstract universal advice.

## Before writing

1. Check there isn't already a skill for this (`.claude/skills/`).
2. If it's about site/app design, wait for real design references (mockups/screenshots)
   before hardcoding visual values — see `design-verify-loop` for how this harness handles
   the loop once you have them.
3. State the trigger in one sentence. Can't → the skill isn't needed yet.

## Keep an index

Maintain a short list somewhere in this project's `AGENTS.md`/`CLAUDE.md` of the skills
that exist, so a new skill isn't accidentally duplicated later.
