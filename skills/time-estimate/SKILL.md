---
name: time-estimate
description: >-
  Turn a task into a defensible time estimate using T-shirt sizing (S/M/L/XL → hour ranges)
  and flag EARLY — not at the deadline — when the work is drifting over. Use when someone
  asks "how long will this take", "estimate this", "size these tickets", "are we going to
  make it", or when planning a sprint / day and you need hours, not vibes. One consistent
  sizing method so estimates are comparable across tasks and people.
user-invocable: true
metadata:
  version: "1.0.0"
  method: "T-shirt sizing + confidence + early-drift flag"
---

# time-estimate

Estimates go wrong in two ways: they're pulled from thin air (so nobody can compare or
defend them), and the "we're over" signal arrives at the deadline, when it's useless. This
skill fixes both — one repeatable sizing method, and a drift flag that fires while there's
still time to react.

## The sizing scale

Map the task to a size, then to an hour range. Estimate in RANGES, never a single number —
a point estimate hides the uncertainty that's the whole point of estimating.

| Size | Hours (range) | Shape of the work |
|---|---|---|
| **S** | 0.5–2h | one clear change, known approach, no unknowns |
| **M** | 2–6h | a few moving parts, one or two small unknowns |
| **L** | 1–3 days | multiple components, real unknowns, needs a plan first |
| **XL** | 3+ days | should be **split** — an XL is a signal to decompose, not to estimate as-is |

An XL is not an estimate; it's a flag that the task is too big to estimate honestly. Break
it into S/M/L pieces and size those.

## Procedure

1. **Restate the task** in one sentence so the estimate is against a clear scope. Vague
   scope is the #1 source of bad estimates — sharpen it before sizing.
2. **Size it** (S/M/L/XL) and give the hour range, plus a **confidence** (high / medium /
   low). Low confidence widens the range — say so, don't fake precision.
3. **Name the top unknown.** The one thing that, if it goes sideways, blows the estimate.
   Naming it is often what turns an L back into an M (or reveals a hidden XL).
4. **Set a drift checkpoint** — a fraction of the estimate (e.g. 50%) at which you re-check.
   If the work isn't ~half done by then, that's the early flag.

## The early-drift flag (the point of the skill)

The value isn't the estimate — it's catching the overrun **while it can still be acted on**.

- At the drift checkpoint, compare actual progress to the estimate. If behind, **flag it
  now**, not at the deadline.
- When you flag, present options, not just a slip: cut scope, add help, extend, or re-plan.
  A flag without a choice is just bad news; a flag with options is useful.
- Re-size the remaining work when you flag — the original estimate is stale the moment
  reality diverges.

## Guardrails

- **Ranges, not points.** A single number is a false promise.
- **Estimate scope, not effort-you-hope-for.** Size the task as it actually is, including
  the boring parts (tests, review, integration), not the happy path.
- **An XL must be split before it's committed to.** Never let an un-decomposed XL sit in a
  plan as if it were a real estimate.
- **Flag early or the estimate was pointless.** The checkpoint is not optional; skipping it
  turns estimation into fortune-telling.
