---
name: step-back
description: Structured diagnosis when stuck — an anti-thrash valve. Invoke when the same approach fails twice in a row (especially during a plan-driven implement step), or manually anytime. Triggers - "step back", "отойди на шаг", "мы застряли", "we're stuck", "diagnose why this keeps failing".
---

When invoked, stop hammering the failing approach and follow this process.

## 1. State the real goal
What did the user originally ask for? The actual outcome, not "make this error go away."

## 2. List what was tried
For each attempt:
- What approach was used
- Specific error or failure mode (not "it didn't work")
- What this rules out

## 3. Classify the blocker
- **Wrong mental model** — misunderstanding how the system works
- **Wrong tool/API** — the tool can't do what we're asking
- **Wrong assumption** — a premise the approach rests on is false
- **Unnecessary complexity** — overengineering the solution
- **Missing information** — need to read more code, check docs, or ask the user

## 4. Propose a different direction
A genuinely different path, not a tweak of the failed approach. Explain why it avoids the identified blocker.

## 5. Wait for confirmation
Present the diagnosis and proposed direction. Do not proceed until the user confirms.

## If working from a plan (`plan.md`)

When a `plan.md` is active, do **not** apply ad-hoc fixes. Propose a **plan revision**
instead: update the relevant section of `plan.md`, get the user's approval, then
resume implementation from the corrected plan. This keeps the plan as the contract
even when an approach fails mid-implement.
