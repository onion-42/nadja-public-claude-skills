---
description: Receive a prior agent's handoff and vet it before touching anything. Ingests the handoff doc (arg = path or pasted text; default the newest handoff.md under .claude/), reads it deeply, restates GOAL / Done / Pending / the single next step, then runs the `roasting` skill on the plan to surface every gray area as multiple-choice questions — and STOPS. The receiving counterpart of the `handoff` skill. Never implements.
argument-hint: "[path to handoff.md | pasted handoff text]"
---

# /pickup-handoff

You are **taking over** work another agent (or a past session) parked. Do the intake, vet it, and
wait — do **not** start the task.

## Step 1 — Load the handoff

- Source, in order: `$ARGUMENTS` if it names a path or contains pasted handoff text; else the most
  recently modified `handoff.md` under `<CWD>/.claude/`. If none is found, ask ONE multiple-choice
  question naming the candidate handoff files you can see (plus a free-text option last).
- Read it **deeply** — every line. If it references `research.md` / `plan.md` in the same folder,
  read those too.

## Step 2 — Restate what you inherited

Reflect it back compactly so the user can confirm you understood the takeover:
- **GOAL** — the objective as the prior agent stated it (the `goal` skill's framing).
- **Done** — what is already completed and verified.
- **Pending** — what remains.
- **Single next step** — the one immediate action the handoff names.
- **Gotchas** — off-disk context the handoff flagged.

## Step 3 — Roast the plan

Run the **`roasting`** skill (team plugin) on the inherited plan end to end: undefined done,
phantom nouns, "somehow" steps, load-bearing assumptions, silent scope, missing failure branches,
unowned decisions, priority collisions. Output its full format — findings quoting the handoff's
actual words, numbered multiple-choice questions, and a verdict. If `roasting` is not installed,
do the same hunt inline.

Roast **the work**, never the writer. Never critique spelling or grammar.

## Step 4 — STOP

Wait for the user's answers. Do **not** implement and do **not** "just start the easy parts". If a
`plan.md` is active, propose diffs to it — never rewrite it silently. Implementation begins only on
the user's explicit go-ahead.
