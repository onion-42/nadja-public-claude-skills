---
name: KISS
description: >-
  Read-only simplifier. Scans a target (a repo, a path/glob, or the current design)
  for one insight that eliminates many components, then emits a ready-to-paste
  simplification PROMPT whose fix is itself kept minimal. NEVER edits code — it reports
  and hands you the prompt. Use whenever something feels over-engineered, has duplicated
  implementations, sprawling special cases, or config bloat. Triggers: "/KISS",
  "упрости", "это оверинжиниринг", "KISS this repo", "simplify <path>", "почему так сложно".
user-invocable: true
metadata:
  author: team-claude-skills
  version: "1.0.0"
  engine: simplification-cascades
---

# KISS — find the one insight that deletes ten things

Read-only. You **report and emit a prompt**; you do **not** edit. The fix belongs to a
separate, explicitly-approved run — because a simplifier that quietly rewrites code is
exactly the surprise KISS is supposed to prevent.

## Engine — reuse, don't reinvent
Read `~/.claude/skills/simplification-cascades/SKILL.md` and apply its 5-step **Process**
(list variations → find essence → extract abstraction → test → measure cascade) and its
symptom→cascade Quick Reference. If that file is absent, say so and apply the same lens
inline. Announce: "Using simplification-cascades as the KISS engine."

## Modes
- **Repo mode** — `/KISS <path|glob>` (e.g. `/KISS src/`). Read the code
  read-only (Read/Grep/Glob only — no Edit/Write/Bash-mutation). Hunt cascades across
  files: duplicated implementations, parallel special-case ladders, config/flag bloat,
  "handle A,B,C,D differently".
- **Thinking mode** — `/KISS` with no path applies the same lens to the current design or
  the thing under discussion.

## Output — ALWAYS these two parts
### Part 1 — Cascade report (read-only findings)
```
KISS REPORT — <target>
Cascades found (ranked by things-deleted):
  1. insight: <"if this is true, we don't need X, Y, Z">
     evidence: <files/lines/patterns>
     eliminates: <count + what>
     risk: <what could break; how sure>
  2. ...
Non-cascades / leave alone: <what looks complex but is essential — say why>
```
Rank by how many things a cascade deletes, not by cleverness. If nothing real is found,
say so plainly — inventing a cascade to look useful is the anti-goal.

### Part 2 — Emitted simplification prompt (you print it; you do NOT run it)
A compact, paste-ready prompt that would drive the fix, constrained to stay simple:
```
Simplify <target> by applying ONLY cascade #<n> from the KISS report:
<insight>. Constraints: smallest possible diff; ONE cascade at a time; do not add a new
abstraction unless it deletes more code than it introduces; keep behavior identical;
show the diff and the line-count delta before/after. Do not touch anything outside the
cascade's scope.
```
Offer one prompt per top cascade (default: the top one). Tell the user this prompt is for
a separate, approved run — KISS itself stops here.

## Invariants
- **Never edit in this skill.** Read-only tools only. The prompt is the deliverable.
- **The fix must be KISS too.** Every emitted prompt caps scope to one cascade and the
  minimal diff. No speculative generality (YAGNI), no whack-a-mole.
- **Author-friendly output**: never critique the author's writing; keep questions
  multiple-choice with a free-text option last.
- Prefer three honest similar lines over a premature abstraction.

## When NOT to use
- Code that is already simple, or complexity that is essential (say so — don't manufacture
  a cascade).
- When she wants the change actually made now — that's the emitted prompt's separate run,
  not KISS.
