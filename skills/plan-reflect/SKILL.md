---
name: plan-reflect
description: Post-task learnings extraction. Use after completing a task, before archiving.
---

Part of the `plan-*` workflow: `/plan-compose` → [work] → `/plan-reflect` → `/plan-archive`.

Extract lasting value from the current session. Scan for what was hard, surprising, or corrected — then write learnings to the right places.

Session transcripts routinely reach several MB — never `Read` one. Parse it line-by-line and keep only the text blocks, then page or grep that (see `/file-reading` → Large and remote files).

## What to look for

- What was hard or surprising
- What the user corrected (patterns, preferences, constraints)
- Patterns settled on during implementation
- Non-obvious external systems, configs, or behaviors encountered
- Decisions the code doesn't explain on its own

## Where to write

1. **Plan's `## Completion` section** — deviations from plan, discoveries, assumption outcomes (AS verified/falsified), UK resolutions. Only fill if the section is empty or incomplete — the user may have filled it already.
2. **`.claude/_cc_learnings_<purpose>.md`** (project-level) — broader patterns and reusable knowledge that don't fit in the plan. Only create if there are learnings beyond what Completion captures. First line: `Associated plan: _cc_plan_<purpose>.md`.
3. **Project docs** (README, docs/) — domain knowledge that belongs with the code, not with CC artifacts.

## Format

Each learning entry:
- **What** — one line
- **Why** — if non-obvious
- **How to apply** — if non-obvious

## What to discard

- Anything obvious from reading the code
- One-off debugging details
- Anything already captured in the plan or docs

## Artifact-reference pass (required)

Before writing learnings, audit the session's changes for plan leakage: grep every file the plan touched (outside `_cc_*` files themselves) for references to the plan or its associated artifacts — plan-internal labels (IV/RK/AS/UK codes, phase numbers), `_cc_plan_*`/`_cc_research_*`/`_cc_learnings_*` names, or "the plan"/"see plan" phrasing in comments. Strip survivors by rewriting them as self-explanatory prose; keep domain-legitimate mentions (specs that genuinely operate on `_cc_*` files, test fixture data). Re-run the relevant checks after any edit. Report what was found and fixed.

## Global learnings

**Never touch `~/.claude/CLAUDE.md` directly.**

If any learnings might be worth making permanent (cross-project patterns, tool behaviors, workflow discoveries), present them to the user:
> "These learnings might be worth promoting to global:"
> - [proposed text]
> - Suggested location: `~/.claude/CLAUDE.md` / `~/.claude/rules/<rule>.md` / user-level memory

The user decides what to promote and where.

## Next step

After reflect, suggest the user run `/plan-archive` to move the plan and related files to archive.
