---
name: goal
description: >-
  Distill a raw, dense, multi-part prompt into an explicit, pinnable GOAL block (primary goal, sub-goals, hard vs soft constraints, ambiguities, definition of done) so a long session doesn't lose the thread when requests drift. Use when the user says "goal", "pin the goal", "what are we even doing", "don't lose the thread", "цель", "зафиксируй цель", or pastes a long dense prompt with several bundled asks. Also run a lightweight drift check when a mid-session message narrows or adds to a goal already pinned this session.
user-invocable: true
metadata:
  version: "1.0.0"
  basis: "Goal-pinning against mid-session drift; the output does the remembering so working memory doesn't have to."
---

# Goal

Turn a raw prompt into an explicit, pinnable **GOAL block** that can be re-read later in the session to catch drift. This skill does not do the underlying task — it distills what the task *is* before work starts, and re-checks it when new messages arrive.

## When to use

- A long, dense, multi-part prompt just arrived (several asks bundled together).
- The user explicitly asks: "goal" / "pin the goal" / "what are we even doing".
- Before a research → plan workflow, to lock the target before drafting.
- A mid-session message looks like it narrows, redirects, or adds to work already in progress — run the **drift check** below instead of restarting from scratch.

## When NOT to use

- A short, single, unambiguous ask ("rename this variable") — no distillation needed.
- The user is mid-answer to a clarifying question you already asked.
- A pure status recap of the session ("what did we just do") — that's `/cho`, not `goal`.

## Procedure

1. Read the raw prompt(s) in full. Do not correct spelling or grammar; mixed languages and transliterated terms carry meaning, not noise.
2. Extract the **primary goal** as ONE sentence (compound if needed) — the outcome that makes everything else in the prompt make sense.
3. Extract **sub-goals** as a numbered `[ ]` checklist. Keep the user's own wording where it carries meaning (exact terms, file paths, thresholds) rather than paraphrasing it away.
4. Name the **target artifact** for each sub-goal that has one — the function, cell, or file that will actually change. "Fix the chart" is ambiguous when three functions draw charts; `plot_monthly_revenue` is not. If the prompt does not pin it down, mark the sub-goal `TARGET: unpinned` and make it the first thing you ask about.
5. Split constraints into **HARD** (must hold — violating it means the task failed) and **SOFT** (nice to have, tradeable under pressure). If nothing reads as soft, say "none stated" — do not invent softness to fill the slot.
6. Flag only **ambiguities that would change the actual work**, as multiple-choice questions — 3–4 concrete options plus a final free-text option ("something else / let me explain"). Don't interrogate for completeness's sake.
7. Name the **definition of done**: the observable artifact or state that proves the goal is met (a file, a number, a diff, a passing check — not a feeling).
8. Emit the pinned **GOAL block** (template below). Restate it at the top of the next turn if the session is long or the thread risks drift.

## Drift check (on resume, or when a new message may have shifted scope)

1. Re-read the last pinned GOAL block, then the message(s) that arrived since.
2. For each existing sub-goal, state one line: **done** / **in progress** / **not started**.
3. Anything new not covered by an existing sub-goal → add as `NEW (added mid-session): ...`.
4. Anything that redefines an existing sub-goal rather than adding to it → flag as `NARROWED: sub-goal N now specifically means ...` — never swap scope silently.
5. Re-emit the updated GOAL block if anything changed.

## Output template

```
GOAL BLOCK [pin — re-read before continuing]
Primary goal: <one sentence>
Sub-goals:
1. [ ] ...
2. [ ] ...
Hard constraints: <bullets, or "none stated">
Soft preferences: <bullets, or "none stated">
Open questions: <MCQ refs, or "none">
Definition of done: <observable artifact/state>
```

---

## Worked example

**Turn 1 (raw prompt):** fix the chart in `sales_report.ipynb` — one chart per region, not a grid; keep the colour legend when saving to SVG; show the median order value per month; then check whether last quarter's export `orders_q2.csv` overlaps this quarter's, and drop duplicates before computing totals.

```
GOAL BLOCK [pin — re-read before continuing]
Primary goal: Fix the per-region chart and remove cross-quarter duplicate orders in
  sales_report.ipynb so the figures and the totals behind them are correct.
Sub-goals:
1. [ ] "one chart per region" — split the current grid into separate charts.
       TARGET: unpinned — three functions draw charts in this notebook.
2. [ ] Keep the colour legend in the SVG export.
3. [ ] Cell value = median order value per month.
4. [ ] Measure order-ID overlap between orders_q2.csv and the current export.
5. [ ] Drop overlapping orders before computing totals.
Hard constraints: one chart per region (not a grid); legend survives SVG export;
  no duplicate order counted twice.
Soft preferences: none stated.
Open questions: Q1 — WHICH chart? A) the top-10 regions ranking B) the monthly trend
  C) the region-by-product heatmap D) something else / let me explain.
Definition of done: notebook re-runs end to end and produces (a) one SVG per region with
  its legend, (b) a logged overlap count, (c) totals with zero duplicate orders.
```

Sub-goal 1 carries `TARGET: unpinned` and Q1 exists **because** step 4 could not name a function.

**Turn 2 (mid-session):** the user answers "the ranking one" and adds: "also make one ranking per metric, not only revenue".

**Drift check output:**
```
Q1 RESOLVED: the top-10 regions ranking.
1. NARROWED: sub-goal 1 now means that one figure, one file per region.
2-3. Re-check against the resolved target first — they may already hold there.
4-5. not started — unchanged by this message.
NEW (added mid-session): one ranking figure per metric, not only revenue.
```
Re-emit the GOAL block with sub-goal 1 replaced and the new sub-goal added before continuing.

**The lesson this example encodes:** an unpinned target (step 4) and an unmeasured assumption are the two things that cost a whole round trip. Catch both in the GOAL block, before the work starts.
