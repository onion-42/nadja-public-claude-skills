---
name: when-stuck
description: Dispatch to the right problem-solving technique based on how you're stuck. Use when stuck and unsure which technique to apply for your specific type of stuck-ness.
when_to_use: when stuck and unsure which problem-solving technique to apply for your specific type of stuck-ness
version: 1.1.0
---

# When Stuck — Problem-Solving Dispatch

## Overview

Different stuck-types need different techniques. This skill helps you quickly pick one.

**Core principle:** match the stuck-symptom to the technique.

Some techniques below are separate skills. `systematic-debugging`, `root-cause-tracing` and
`dispatching-parallel-agents` ship in the **team** plugin. If a named skill is not installed, apply
the one-line description in the table inline and say that you are doing so.

## Stuck-Type → Technique

| How you're stuck | Technique | What it does, in one line |
|---|---|---|
| **Complexity spiralling** — same thing 5+ ways, growing special cases | simplification-cascades | Find the one insight that makes several components unnecessary. |
| **Need innovation** — conventional solutions don't fit | collision-zone-thinking | Ask "what if we treated X like Y?" with an unrelated domain. |
| **Recurring patterns** — same issue in different places | meta-pattern-recognition | Name the shared pattern across 3+ instances, then solve it once. |
| **Forced by assumptions** — "it must be done this way" | inversion-exercise | Flip the core assumption and see what becomes possible. |
| **Scale uncertainty** — will it hold in production? | scale-game | Test the idea at extremes (1, 1000, 1M) to expose what breaks. |
| **Code broken** — wrong behaviour, failing test | systematic-debugging | Root-cause investigation before any fix. |
| **Multiple independent problems** | dispatching-parallel-agents | Investigate independent failures in parallel. |
| **Root cause unknown** — symptom clear, cause hidden | root-cause-tracing | Trace backward from the symptom to the origin. |

## Process

1. **Identify the stuck-type** — which symptom matches?
2. **Load that skill** (or apply the one-liner inline).
3. **Apply the technique** — follow its process.
4. **Still stuck?** Try a different technique or combine two.

## Combining techniques

- **Simplification + meta-pattern:** find the pattern, then simplify every instance.
- **Collision + inversion:** force a metaphor, then invert its assumptions.
- **Scale + simplification:** extremes reveal what to eliminate.

## Remember

- One technique at a time.
- Write down what you tried, so the next attempt doesn't repeat it.
