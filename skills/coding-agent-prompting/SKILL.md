---
name: coding-agent-prompting
description: Reference for prompting reasoning models and coding agents - favors a short reasoning summary over "think step by step", hunts contradictions, applies coding-prompt priorities (Safety > Accuracy > Instructions > Style), places critical facts for long context, and judges agents by outcomes. Use when drafting or debugging prompts for reasoning/coding models, or when setting up an agent/TDD workflow. Triggers - "prompt for the model", "why is the agent jumpy", "how should I phrase this for Opus/Sonnet", "reasoning model prompt".
---

# Coding-agent & reasoning-model prompting

Cross-session reference knowledge. Not loaded every session — it loads when the task is
actually about prompting a reasoning/coding model or wiring an agent workflow.

## Reasoning models

- **Don't say "think step by step".** Ask for a short **reasoning summary** instead —
  strategy + assumptions + edge cases, not the full chain of thought.
- Reasoning models are **literal**. On conflicting instructions they favor the one nearer
  the prompt's **end**. Hunt and remove contradictions; "jumpy" answers are the tell of a
  bad prompt, not a bad model.

## Coding prompts

- **Priority order: Safety > Accuracy > Instructions > Style.**
- Useful nudges: a **role**, "production-ready", "diff/patch only", "tests first then code"
  (TDD), and "if unsure, ask".

## Long context

- The **middle is lost** — put critical facts at the **start AND the end**.
- Prefer **Compress → Retrieve → tool-access on demand**: Gitingest to compress; ripgrep,
  then embeddings + rerank to retrieve; reach for tools only when needed. MCP is powerful
  but token-expensive — use cheap code/tool calls for routine ops.

## Judging agents

- Judge by **iterations-to-green-tests** and **PR-accepted ratio**, not by tokens spent.

## Bioinformatics edge (resume story)

- A domain `AGENTS.md` "tester-bioinformatician" for mass TDD is both a real workflow and a
  strong resume story.

## Related

- Drafting help: the `prompt-engineering` skill (strong prompts before big tasks) and the
  `prompt-optimizer` skill (vendored locally, was ECC).
- Subagent model routing: `~/.claude/rules/common/model-routing.md`.
