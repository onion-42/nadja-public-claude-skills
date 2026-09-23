---
name: cho
description: >-
  Quick "what's going on?" status of the CURRENT session: what we're working on, what's done,
  what's next, any blockers. A look back, not new work. Triggers: "/cho", "what's going on",
  "where are we", "catch me up", "session status", "remind me where we stopped",
  "че происходит", "где мы".
user-invocable: true
---

# cho — "what's going on?"

When the user calls `/cho` (or asks "what's going on", "where are we", "where did we stop"), give a
short status of the CURRENT session. Do not start new work and do not launch tasks.

## Reply format (short, no filler)

**Now:** one sentence — what we are working on right now.
**Done:** 2–4 items — what is finished in this session.
**Next:** 1–2 items — the nearest next step.
**Blockers:** what is in the way and what is needed from the user; if nothing — "none".

## Rules

- Use the REAL session context: what was done, which files were touched, how it ended, what is
  still open. If the context was compacted, a handoff or summary file may help — but never invent
  progress.
- Keep it under ~120 words, in full sentences, not fragments.
- If there was a plan or todo list, show which steps are done / in progress / pending.
- `/cho` changes nothing and runs tools only if it truly needs to read something.
- If the session just started and nothing is going on yet, say so and suggest where to begin.
- Reply in the language the user used.
