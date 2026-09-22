---
name: handoff
description: >-
  Package the CURRENT task's live state into one compact, resumable handoff document —
  the GOAL, what's Done, what's Pending, the single immediate next step, and gotchas
  discovered this session that aren't yet on disk — written to a file another mind can
  resume from. Use whenever work has to survive a boundary and the scrollback might not
  carry it: ending a session, before a /compact, handing the baton to another agent or a
  future session on another machine, or pausing to pick up later. Trigger on "handoff",
  "hand this off", "package the state", "prep a resume doc", "save context, I'm stopping"
  — even when no file is named. This is the LIGHTWEIGHT portable resume doc.
user-invocable: true
metadata:
  version: "2.0.0"
  basis: "goal-pinning + a fixed, minimal document shape"
---

# Handoff

Turn the live, in-your-head state of the current task into **one file another mind can
resume from** — a later you, a fresh session after `/compact`, a different agent, or the
same task reopened on another machine.

The disk survives what the conversation does not. Scrollback gets compacted, sessions end,
machines change. Anything that only lives in the chat is the first casualty. Handoff is the
deliberate act of moving the *non-obvious, forward-looking* part of the session onto disk
before that boundary hits.

## When this fits (and when it doesn't)

Reach for handoff whenever the work needs to cross a gap: end of session, before a
compaction, passing to another agent, or just parking a task to resume later.

It is deliberately **not** two neighbours it's easy to confuse with:

- A **full session dump** (everything, machine-local) is heavier. Handoff is the lean,
  portable counterpart — a single readable doc you (or another agent) can paste and
  continue from anywhere.
- A **backward-looking summary** narrates what happened. Handoff looks *forward* — what's
  next. Don't turn it into a chronicle.

If everything important is already on disk (committed, in a plan file), a handoff can
legitimately be three lines — GOAL, next step, "rest is on disk." Short is a success, not a
failure.

## Where it goes

Write to `.claude/<task-name>/handoff.md` under the current project (create the directory
if missing; use the same kebab-case `<task-name>` as this session's other artifacts). If
the project isn't a git repo or you're outside one, any stable path both you and the
resumer can reach is fine — the location matters less than the content.

## The document

Write exactly this shape. It is small on purpose — every section earns its place by
answering a question the resumer will ask.

```markdown
# Handoff — <task-name>

## GOAL
<the primary goal in ONE sentence — if it won't compress to one sentence, the goal is
still fuzzy; sharpen it before writing the rest>

## Current State
Done:
- <what is actually finished and verified>
Pending:
- <what remains, concretely>

## Immediate Next Step
<ONE concrete action to start with — not a list>

## Gotchas Discovered
- <a constraint, trap, or decision found THIS session that is NOT already on disk>
- <"none" if everything important is already committed / in a plan file>
```

## Procedure

1. **Resolve `<task-name>`** and the artifact directory (see "Where it goes").
2. **Write the GOAL as one sentence.** The one-sentence limit is the point: if it won't
   compress, the goal is still fuzzy — clarify it, don't pad the block.
3. **Snapshot Done vs Pending.** Prefer a TodoWrite list if one exists; otherwise read it
   off the session. Report what is *actually* done and verified — aspirational "done" is
   how a resume goes wrong.
4. **Name the single immediate next step** — one concrete action, the thing you'd do in the
   next 5 minutes. A list here defeats the purpose; the resumer needs a foothold, not a
   backlog.
5. **List gotchas discovered this session that aren't on disk** — a non-obvious constraint,
   a trap you hit, a decision and its rationale. Skip anything already committed or in a
   plan file; duplicating disk just bloats the doc. "none" is a fine answer.
6. **Write the file, then tell the user its path.** Do **not** start executing the
   underlying task — handoff prepares the baton, it does not run the next leg.

## Why the shape holds up

- **Forward, not backward.** Done/Pending exist only to frame the next step, not to narrate
  history. The resumer's first question is "what do I do now?" — answer it above all.
- **One next step, not many.** Ambiguity about where to start is what actually stalls a
  resumed session. Pick the single foothold; the rest is Pending.
- **Only off-disk gotchas.** The whole value is capturing what compaction/session-end would
  erase. Re-listing what's already committed hides the signal.

## Related

- **`strategic-compact`** decides *when* to compact; its handoff mode delegates the
  state-packaging to this skill. When the boundary is specifically a compaction, pair the
  two: a `/compact` focus line plus a resume prompt with the GOAL pinned at both ends.
