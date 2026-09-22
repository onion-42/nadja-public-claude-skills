---
name: model-route
description: >-
  Decide which model tier and reasoning effort each subagent should get before you spawn
  it — routing by how pre-specifiable the task is, not by the label on it. Use whenever
  you are about to dispatch subagents (the Agent tool, a Workflow fan-out, or any parallel
  task set) and want to spend tokens well: "which model for this subagent", "should this be
  a cheaper model", "how many agents should I fan out", "is high effort worth it here". Also
  use when a plan proposes a wide fan-out and you need to justify the width and effort per
  step. Encodes a routing POLICY; the model mechanism itself is the `model:`/`effort` config
  on the subagent.
user-invocable: true
metadata:
  version: "1.0.0"
  note: "Deliberately names no specific model IDs — the lineup changes faster than this file."
---

# model-route

Anthropic ships the *mechanism* for per-subagent model choice (the `model:` field in a
subagent definition, and a reasoning-effort setting) but no *policy* for it. This skill is
the policy: a small decision procedure so subagent routing is a deliberate choice, not a
reflex to reach for the biggest model or the widest fan-out.

## The one axis that matters: pre-specifiability, not task type

Before every spawn, ask one question:

> Can I write down the steps this subagent must take, and how I'll know it succeeded?

The answer routes the work. Task *labels* ("research", "refactor", "review") do not —
"research" can be a 5-minute lookup or an open-ended investigation, and those route
oppositely.

| Signal | Route |
|---|---|
| **Pre-specified** — concrete file/source list + acceptance criteria; ≤2 judgment calls | baseline tier, **low** effort |
| **Ambiguous** — steps not enumerable up front; the subagent must decide what matters as it goes | baseline tier, **raise effort** (medium/high) — not the tier |
| **Purely mechanical** — grep a field, count, rename, reformat (deterministic string ops) | **cheapest** tier that can do it |

**Anchor the baseline tier and hold it constant.** The baseline is a single, cost-efficient
*capable* model — the same one for almost everything. Only *effort* moves up; the tier does
not. Setting the baseline to your most expensive tier "to be safe" silently defeats the whole
point, so name a mid tier as baseline and justify any deviation.

Two moves, in priority order: **raise effort before you raise tier**, and **drop to a cheaper
tier only for genuine mechanics** — where "mechanics" means a deterministic string operation.
Beware the extract trap: pulling a field out of structured text with grep is mechanical
(cheapest tier); *reading sample sizes out of papers' prose* is comprehension — that is
pre-specified work at low effort on the baseline tier, **not** cheapest-tier mechanics.

## Priority order (highest first)

1. **Spend your OWN tokens on the prompt, not on the effort dial.** Before raising effort,
   try to make the task specifiable — pick the sources, name the files, define "done".
   That is the dispatching agent's job. A subagent that needs high effort is often a prompt
   that wasn't finished.
2. **High effort is a fallback, not a default.** Justify it in one line: state what could
   not be pre-specified.
3. **Cap the width.** More than ~5 parallel subagents → stop and reconsider (or ask the
   human). Fan-out width costs more than the effort dial, and thoroughness theatre (30
   agents where 5 would do) is the most expensive mistake.
4. **Cheaper tier needs a reason (mechanics); higher effort needs a reason (real ambiguity).**

## In a plan (state routing before approval)

When a plan proposes subagents, declare, per step:
- the effort level (and where a step is pure mechanics, the cheaper tier);
- how many subagents;
- one line for each medium/high-effort subagent explaining what is *not* pre-specifiable.

This lets a reviewer catch an over-powered or over-wide fan-out before it runs.

## Anti-patterns

- Routing by the word "research".
- Reaching for a cheaper tier to "save money" when a capable model at low effort is already
  cheap — and correct more often, so it finishes without a second pass.
- Handing a low-effort subagent an open-ended "figure out what's wrong" brief. That's either
  higher-effort work or a badly written prompt — decide which.
- Raising effort because the task feels *important*. Importance is not ambiguity.
- Fan-out width chosen for thoroughness theatre.

## The consequence

Plan quality is the router. A plan with an explicit file list and acceptance criteria
routes to a capable model at low effort; a vague plan forces higher effort or a wasted pass.
Every gray area you remove from the prompt can drop a subagent's effort a notch — that is the
token saving.
