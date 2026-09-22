# team-claude-skills

A curated, **team-usable** bundle of Claude Code skills and subagents focused on one goal:
**spend tokens well — finish tasks without spawning new ones.** Better planning, durable
handoffs, cheap-but-correct model routing, evidence-grounded research, and study artifacts
from a codebase.

Nothing here is personal. No budgets, no chat bots, no note-taking, no per-person config
sync. Every skill is written to work for any engineer on a team.

## What's inside

Browse the **card site** at [`site/index.html`](site/index.html) (open it in a browser) for
a filterable view. In short:

**Token economy & context**
- `handoff` — package live task state into one resumable doc before a boundary
- `strategic-compact` — decide *when* to compact, and hand off cleanly when you do
- `deep-research` — multi-agent research with citation-traceable output
- `plan-compose` / `plan-reflect` / `plan-archive` — durable, on-disk planning

**Thinking & prompting**
- `step-back`, `KISS`, `roasting`, `prompt-engineering`, `coding-agent-prompting`
- `systematic-debugging`, `root-cause-tracing`

**Orchestration**
- `agent-bus` — a file-based group chat + claims + optional S3 bridge for cross-machine
  agents. **File-first handoff protocol**; bring your own S3 bucket.
- `dispatching-parallel-agents`, `model-route` (route by pre-specifiability, not task label)

**Skill infrastructure**
- `skill-creator`, `testing-skills-with-subagents`, `eval-harness`, `writing-skills`

**Research & docs**
- `research-cite`, `find-docs`

**New in this bundle**
- `repo-anki-mindmap` — turn a repo into an Anki deck (.apkg) + an interactive mind-map
- `rag-eval` — evaluate a RAG system with Ragas (faithfulness, retrieval quality)
- `brainstorm` — dialectical debate that **remembers** the discussion across turns

**Subagents** (`agents/`)
- `test-runner` (failures-only, token-frugal), `code-reviewer`, `security-reviewer`,
  `external-researcher`

## Install

Copy the skills and agents into your Claude Code config:

```bash
# per-project
cp -r skills/*  <your-repo>/.claude/skills/
cp -r agents/*  <your-repo>/.claude/agents/

# or user-wide
cp -r skills/*  ~/.claude/skills/
cp -r agents/*  ~/.claude/agents/
```

Some skills ship a helper script (`agent_bus.py`, `build.py`, `eval_rag.py`) — reference it
by its installed path. Python skills that need a library say so in their SKILL.md
(`genanki`, `markmap`, `ragas`, `boto3`); install only what you use.

## Two things you must set yourself

- **`agent-bus` S3 path** — cross-machine sync needs a bucket *your org owns*:
  `export AGENT_BUS_S3="s3://YOUR-BUCKET/YOUR-PREFIX/agent-bus/"`. Unset = local-only, clean
  no-op.
- **`rag-eval` judge model** — Ragas uses an LLM as judge; set it to a model your org
  permits (`RAG_EVAL_PROVIDER` + that vendor's key). The harness refuses to run otherwise,
  so the choice is always explicit.

## Testing

The net-new and modified skills (`repo-anki-mindmap`, `rag-eval`, `brainstorm`, `agent-bus`,
`model-route`, and the `test-runner` agent) are exercised with `testing-skills-with-subagents`;
see [`tests/eval-results/`](tests/eval-results/). Adopted skills carry their upstream tests
and are smoke-checked here for valid frontmatter and trigger descriptions.
