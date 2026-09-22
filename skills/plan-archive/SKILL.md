---
name: plan-archive
description: Archive a completed plan — move files, update STATUS, write INDEX entry.
disable-model-invocation: true
---

# /plan-archive

Archive a completed `_cc_plan_*` after the user confirms the task is done.

## Prerequisites

Before running `/plan-archive`, ensure:
- `/plan-reflect` has been offered and either run or declined.
- The plan's `## Completion` section is filled (by `/plan-reflect` or manually). If empty, warn and ask the user whether to fill it now or archive without it.

If prerequisites are not met, warn and stop.

## Steps

Follow in order — do not reorder.

1. Find all plan-related `_cc_*` files: `_cc_plan_*`, `_cc_research_*` in the project root, and `.claude/_cc_learnings_*` matching the plan's name. List them and confirm with the user before proceeding.
2. If multiple `_cc_plan_*` files exist, ask the user which one to archive.
3. Create `<project-root>/.claude/archive/` if it doesn't exist.
4. Update the plan's STATUS to `ARCHIVED (originally: <original-path>, completed: <date>)`.
5. Move `_cc_plan_*` and `_cc_research_*` to `<project-root>/.claude/archive/`.
6. Move matching `<project-root>/.claude/_cc_learnings_*` to `<project-root>/.claude/archive/`.
7. Append one-liner to `<project-root>/.claude/archive/INDEX.md` (create if missing). Format: `- <filename> — <one-line summary>. Completed <date>.`

## Notes

- `<project-root>` = the working directory where CC was invoked. NEVER `~/.claude/`.
- `_cc_snapshot_*` and `_cc_snapshot_env.md` are session handoff artifacts, not plan artifacts. Do not touch them.
- If no `_cc_plan_*` is found, say so and stop.
