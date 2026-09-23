---
name: mini-reflection
description: >-
  A short, warm end-of-task reflection: what the user did today, one "next time try",
  one specific praise — at most 8 lines, no shame. Written by Claude itself, on request or at the
  end of a task when the user has asked for reflections. Triggers: "/mini-reflection",
  "quick reflection", "wrap up", "reflect on this task", "мини-рефлексия", "подведи итог".
user-invocable: true
---

# mini-reflection — about the user, forward-looking

A light, three-line look back at the task that just finished. It is about the **user's** way of
working, not about the assistant, and it looks forward, not at mistakes.

## Format (≤8 lines, warm, no shame)

- **🪞 You today:** one concrete thing the user did or decided, and what it says about how they work.
- **💬 Next time try:** quote their real wording or decision → a better move and WHY it helps
  Claude help them. Forward-looking; not a "mistake", not self-criticism.
- **🌱 Praise:** one specific thing done well (quote the real thing).

Optionally, a fourth line **📝 Card:** one flashcard-worthy lesson, only if the session really
produced one. "No card today" is a normal outcome.

## Rules

- Use the REAL session context; never invent.
- Spelling, grammar and typos are never a finding. Intent matters more than orthography.
- Unfinished items go in one `- [ ]` list after the reflection, so nothing is lost between sessions.
- If the user wants it saved, append it to a file they name (for example `reflection.md` next to
  the task's notes). Do not write files unasked.
- Reply in the language the user used.
