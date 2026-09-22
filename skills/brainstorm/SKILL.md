---
name: brainstorm
description: >-
  Multi-agent dialectical brainstorming and decision-support that REMEMBERS the
  discussion across turns and sessions. Runs three opposing personas (Builder,
  Adversarial Critic, Pragmatic Analyst) against a decision, flags cognitive biases
  each turn, ends with a synthesis and concrete next steps — and appends every round
  to a durable debate log so a later turn continues the thread instead of restarting
  it. Use whenever someone is weighing a non-trivial choice, designing an architecture
  or workflow, stress-testing a plan, asking "should I do X or Y", worrying they've
  missed something, or says brainstorm, debate, roast this idea, poke holes in this —
  even without naming the skill. Prefer it over a single-voice answer when the decision
  is hard to reverse or the person sounds unsure.
user-invocable: true
metadata:
  version: "2.0.0"
  basis: "dialectical debate + persistent history (the 'chat history' upgrade)"
---

# brainstorm

A single-voice answer tends toward confirmation bias: it defends the first framing
instead of attacking it. This skill forces friction — three personas that genuinely
disagree — so weak assumptions surface *before* effort is committed. And because a
hard decision is rarely settled in one turn, it keeps a **debate log** on disk, so the
next turn resumes the argument with full memory instead of re-litigating from zero.

## When to run

Trigger on: architecture and tooling choices, "X vs Y" questions, plans someone wants
pressure-tested, migrations, and any moment someone asks to have an idea challenged or
roasted. Skip it for simple factual questions or one-step tasks — the overhead isn't
worth it there.

## The debate log (the "chat history" upgrade)

The whole point of remembering is that a decision evolves — new constraints appear, an
option gets killed, a new one emerges. Losing that between turns means re-arguing
settled points. So:

1. **Resolve a topic slug** from the decision (kebab-case), derived from its core nouns.
   **Reuse the exact same slug every turn** — before minting a new file, check
   `.brainstorm/` for a near-match slug and continue that log instead. A drifting slug
   (`k8s-vs-vm` one turn, `kubernetes-migration` the next) orphans the history and
   re-litigates settled points.
2. **Log path:** `./.brainstorm/<slug>.md` under the current working directory (create
   `.brainstorm/` if missing; add it to `.gitignore` if the CWD is a git repo — the log
   is working memory, not a committed artifact).
3. **On start, READ the log if it exists — and say so.** Open the debate at the last
   state: what's already agreed, what was ruled out and why, the open trade-off. Do NOT
   repeat rounds already in the log — advance from them. **Make the read observable:** at
   the top of your reply, print the resolved slug + the log path, and echo the prior
   `State:` line you loaded (or `no prior log — creating one`). A skipped read must be a
   visible claim, not a silent one.
4. **After each round, APPEND to the log** in this shape:

```markdown
## Round <n> — <ISO date> — <one-line focus>
- **Decision framing:** <the real question this round sharpened>
- **Builder:** <position>
- **Critic:** <challenge + bias flagged>
- **Analyst:** <trade-off vs constraints>
- **State:** agreed=<...> ruled-out=<... + why> open=<the live trade-off>
- **Next step:** <the one concrete action if the thread stops here>
```

The `State` line is what a future turn reads first — keep it truthful and current.

## Personas

Instantiate at least three, at least two fundamentally opposed:

1. **Builder** — argues for the ambitious version: scale, speed, impact. Assumes the
   upside is real and asks what it would take to capture it.
2. **Adversarial Critic** — attacks the Builder directly. Hunts unstated assumptions,
   edge cases, hidden cost, the failure mode nobody named. Never concedes politely
   without new evidence.
3. **Pragmatic Analyst** — neutral. Weighs cost, maintenance, and operational risk
   against the real constraints and reasoning style of the person deciding.

Spawn a domain expert as a fourth voice only when the debate hits a technical deadlock
the three generalists can't resolve.

## Workflow

1. **Parse** the decision into its real question and the constraints that actually bind
   (time, money, skill, reversibility). Read the debate log first if one exists.
2. **Debate**, max three turns per persona so it can't loop:
   - Turn 1 (Thesis): Builder proposes.
   - Turn 2 (Antithesis): Critic challenges assumptions and names the cognitive biases
     in play (sunk cost, planning fallacy, availability, confirmation).
   - Turn 3 (Synthesis): Analyst weighs trade-offs against the constraints.
3. **Synthesis & roast:** state what the personas agree on, the irreducible trade-off
   that remains, one last pass on the weakest surviving assumption, then concrete
   recommended next steps.
4. **Append the round to the log.**

## Guardrails

- **Forbid premature consensus:** a persona may only concede when given new evidence,
  never to be agreeable.
- **Every turn names at least one bias** it's guarding against — that's the exercise,
  not decoration.
- **Keep the real constraints in view;** a brilliant plan the person can't execute this
  month is a failed plan.
- **The log is memory, not a transcript dump.** Record positions, the reason a thing was
  ruled out, and the live trade-off — not the full prose of every persona line.

## Output structure

- **TL;DR** — 1-2 complete sentences.
- **Body** — the debate and synthesis; complete sentences, no fragments.
- **Reasoning summary** — 2-3 sentences on the logic behind the recommendation.
