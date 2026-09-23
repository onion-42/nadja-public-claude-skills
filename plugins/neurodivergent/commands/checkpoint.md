---
description: Create, verify or list named workflow checkpoints (git SHA + log line) so you can see what changed since a known-good point.
argument-hint: "[create|verify|list|clear] [name]"
---

# Checkpoint Command

Create or verify a checkpoint in your workflow.

## Usage

`/checkpoint [create|verify|list] [name]`

## Create Checkpoint

When creating a checkpoint:

1. Ensure current state is clean (tests pass, no uncommitted breakage)
2. Create a git stash or commit with checkpoint name
3. Log checkpoint to `.claude/checkpoints.log`:

```bash
mkdir -p .claude
echo "$(date +%Y-%m-%d-%H:%M) | <name> | $(git rev-parse --short HEAD)" >> .claude/checkpoints.log
```

4. Report checkpoint created

## Verify Checkpoint

When verifying against a checkpoint:

1. Read checkpoint from log
2. Compare current state to checkpoint:
   - Files added since checkpoint
   - Files modified since checkpoint
   - Test pass rate now vs then
   - Coverage now vs then

3. Report:
```
CHECKPOINT COMPARISON: $NAME
============================
Files changed: X
Tests: +Y passed / -Z failed
Coverage: +X% / -Y%
Build: [PASS/FAIL]
```

## List Checkpoints

Show all checkpoints with:
- Name
- Timestamp
- Git SHA
- Status (current, behind, ahead)

## Workflow

Typical checkpoint flow:

```
[Start] --> /checkpoint create "feature-start"
   |
[Implement] --> /checkpoint create "core-done"
   |
[Test] --> /checkpoint verify "core-done"
   |
[Refactor] --> /checkpoint create "refactor-done"
   |
[PR] --> /checkpoint verify "feature-start"
```

## Arguments

$ARGUMENTS:
- `create <name>` - Create named checkpoint
- `verify <name>` - Verify against named checkpoint
- `list` - Show all checkpoints
- `clear` - Remove old checkpoints (keeps last 5)
