---
name: plan-compose
description: Plan file templates and structure for _cc_plan_* files. Auto-invoked when creating or updating plan files. Covers full vs lite format, IPA definitions, phase/risk format, brevity rules, and completion steps.
---

## Plan file structure

**Full** (medium/large tasks) — see [full-template.md](full-template.md): STATUS line, Research link (if exists), then sections: Context, Goal, Design (with IPA — Invariants, Premises, Assumptions), Plan (with phases), Checklist, Completion.

**Lite** (small tasks — single file, single concept) — see [lite-template.md](lite-template.md): STATUS line, then Goal + Plan + Checklist only. Skip Design/IPA.

User confirms classification. Default to full when unsure.

## IPA — Invariants, Premises, Assumptions (under Design)

- Invariants (IV) — hard constraints that must hold. `IV1 — <constraint>`
- Assumptions (AS) — premises marked `[verified]` or `[unverified]`. `AS1 [unverified] — <premise>`
- Unknowns (UK) — open questions to resolve. `UK1 — <question>`

## Plan phases

- Format: `### PH1: <name>` with numbered steps.
- Each step references concrete locations: `file.py:120-160 — <what changes and why>`.

## Considerations and trade-offs

Key design decisions, alternatives considered, why this approach over others.

## Risks

- Format: `RK1 — <risk + mitigation>`

## Brevity rules (all `_cc_*` files)

- Omit sections with nothing to say — don't write "None" or "N/A".
- Evidence only on surprise — passed checks get one line, failures get detail.
- Don't re-narrate what git shows — SHA + short name, not prose diff summaries.
- One sentence per item unless it genuinely can't fit.

## Completion (filled at end of plan)

- Outcome, assumption check results, UK resolutions, deviations from plan.

When the task is done, the workflow continues: `/plan-reflect` (learnings extraction, optionally fills Completion) then `/plan-archive` (move to archive).
