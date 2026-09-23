---
name: repo-tidy
description: >-
  Find dead, orphaned, duplicated, or misplaced files in a repository and PROPOSE a
  cleanup — never delete on its own. Use when someone says "tidy this repo", "what's dead
  code here", "clean up the project", "find unused files", "this directory is a mess", or
  before a release when the tree should be lean. Produces a grouped report of candidates
  with a reason for each; acting on it is a separate, explicit step.
user-invocable: true
metadata:
  version: "1.0.0"
  safety: "proposal-only by default — irreversible actions need an explicit second step"
---

# repo-tidy

A repo accumulates cruft: files nothing imports, scripts superseded twice over, notes in
the wrong folder, two copies of the same helper. This skill *surfaces* that cruft as a
reviewable report. It does **not** delete or move anything on its own — a wrong "dead file"
guess that gets auto-deleted is exactly the failure this skill is built to avoid.

## The one hard rule

**Propose, never auto-act.** The default output is a report of candidates. Deleting or
moving files is a separate step the user explicitly approves, item by item or group by
group. When in doubt about whether something is truly dead, it goes in the report as a
question, not in a delete list.

## What counts as a candidate

- **Orphaned** — a file nothing references: no import, no include, not named in config,
  build files, CI, or docs. (Grep the whole tree for the basename before calling it dead.)
- **Superseded** — an older version alongside its replacement (`foo_old.py`, `foo.bak`,
  `foo copy.py`, `foo_v1` next to `foo_v2`).
- **Duplicated** — two files with the same content (or near-identical helpers) that should
  be one.
- **Misplaced** — a file whose location contradicts the repo's own convention (a test
  outside the test dir, a doc in `src/`, a data file in code).
- **Generated** — build output / caches committed by accident (`__pycache__`, `dist/`,
  coverage files) that belong in `.gitignore`.

## Procedure

1. **Scope it.** Confirm which path/glob to scan (default: the repo root, excluding
   `.git/`, `node_modules/`, `.venv/`, and anything already gitignored).
2. **Detect, don't guess.** For each candidate, establish the *evidence*: the grep that
   found zero references, the sibling that supersedes it, the convention it violates.
   A candidate with no evidence line does not go in the report.
3. **One logged pass.** If the scan runs a script over many files, run it once with a log
   (see the batch-driver pattern), not an interactive file-by-file crawl.
4. **Write the report** to `.claude/repo-tidy/report.md` (create the dir; gitignore it).
   Group by category, and for each item give: path, category, one-line evidence, and a
   suggested action (delete / move-to / merge-into / gitignore).
5. **Stop.** Present the report. Do not act on it in the same step.

## Acting on the report (the explicit second step)

Only when the user approves specific items:
- Prefer **`git mv`** / **`git rm`** so every change is tracked and revertible with a single
  `git revert`.
- Move in groups the user OK'd, not the whole report.
- Leave a one-line note where a moved file used to live if anything might still look for it.

## Guardrails

- **Zero references is necessary, not sufficient.** Dynamic imports, reflection, string-built
  paths, and entry points named only in CI can make a "dead" file live. Flag those as
  *uncertain*, not *dead*.
- **Never touch `.git/`, secrets, or lockfiles** as cleanup candidates.
- **A tidy that deletes something needed is worse than no tidy.** Bias toward the report
  and the question; let the human pull the trigger.

## When NOT to use

- A repo already clean, or a single obvious stray file — just handle it, no report needed.
