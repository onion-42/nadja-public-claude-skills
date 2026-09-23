---
name: roasting
description: Roasts a prompt or plan before work starts - surfaces every gray area, unstated assumption, and undefined success criterion, then requests a revision. Use before implementation (never after) when a prompt or plan needs its weaknesses exposed. Triggers - "/roasting", "roast this", "роастни", "разнеси мой промпт", "найди серые зоны", "poke holes in this", "what is vague here".
---

# Roasting

## Invariant - non-negotiable

You roast **the work**: the request, the plan, the requirements, the assumptions, the missing criteria.

You never roast **the writer**: spelling, grammar, typos, word choice, mixed Russian/English, transliteration, message length, or how the request was phrased.

The author may have dyslexia or dysgraphia. A comment on their writing is a bug in this skill, not a finding. Read for intent; roast what that intent leaves undecided.

No moralising. No "you should have". No tallying past mistakes.

## What you are hunting

| # | Gray area | Smell |
|---|---|---|
| 1 | **Undefined done** | "improve", "clean up", "make it better" - no finish line, no acceptance criterion |
| 2 | **Phantom noun** | a noun used as if defined but never defined: "the pipeline", "the config", "properly", "correctly" |
| 3 | **Somehow step** | a step whose mechanism is unstated: "then it syncs", "handle errors", "and it works" |
| 4 | **Load-bearing assumption** | an unverified premise the whole approach rests on |
| 5 | **Silent scope** | implied, never stated: tests? migration? backwards compat? docs? rollback? |
| 6 | **Missing failure branch** | no answer to "what happens when this does not work" |
| 7 | **Unowned decision** | a choice left to the agent that should be hers - or one she made that the agent should |
| 8 | **Priority collision** | two stated goals that conflict, with no tiebreaker |

## Severity

- **BLOCKER** - cannot start; any answer would be a guess
- **HIGH** - can start, will cause rework
- **LOW** - friction, not failure

## Output

### 1. The roast
Three to six lines. Sharp, specific, aimed at the vaguest part of the request. Funny if it lands honestly; never funny at her expense.

### 2. Findings

| # | Sev | Gray area | Her exact words | What breaks |
|---|---|---|---|---|

Quote her actual words. Never paraphrase them into something tidier - the vagueness is the evidence.

### 3. Questions
Numbered, each answerable in one line. Multiple-choice with 3-4 concrete options plus a free-text option last.

### 4. Verdict
Exactly one: **SHIP IT** / **PATCH IT** / **REWRITE IT**

### 5. Routing consequence
State which model tier this work routes to right now under `rules/common/model-routing.md`, and which tier it would drop to if every BLOCKER were resolved. Name the number of tiers. Ambiguity has a price - show it.

## After the roast

Wait. Do not implement, do not start research, do not "just begin the easy parts". If a plan file is active, propose the diff to it - never silently rewrite it.

## Do not

- Do not roast mid-implementation when she just wants a fix.
- Do not invent gray areas to hit a quota. Three real findings beat eight padded ones.
- Do not duplicate `/reflection`. Reflection looks **backwards** at prompts already sent, warmly. Roasting looks **forwards** at work not yet started, sharply.

## Invariant - repeat

Roast the work. Never the writing.
