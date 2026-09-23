# team-claude-skills

> **TL;DR.** Two Claude Code plugins in one marketplace. `team` has 30 workflow skills and 4 agents
> that help you spend tokens well and finish tasks without starting new ones. `neurodivergent` is an
> opt-in set of comfort tools for ADHD, autistic and dyslexic users. Install:
> `/plugin marketplace add onion-42/nadja-public-claude-skills`, then `/plugin install team@team-claude-skills`.
> Browse the cards and a live demo deck on the [site](https://onion-42.github.io/nadja-public-claude-skills/site/).

A curated, **team-usable** bundle of Claude Code skills and subagents focused on one goal:
**spend tokens well — finish tasks without spawning new ones.** Better planning, durable
handoffs, cheap-but-correct model routing, evidence-grounded research, and study artifacts
from a codebase.

Nothing here is personal. No budgets, no chat bots, no note-taking, no per-person config
sync. Every skill is written to work for any engineer on a team.

It is a Claude Code **plugin marketplace** with two plugins:

- **`team`** (`plugins/team/`) — the workflow skills and subagents below.
- **`neurodivergent`** (`plugins/neurodivergent/`) — opt-in comfort tools for ADHD, autistic
  and dyslexic users (see below). It works best alongside `team`.

## ⟐ What's inside

Browse the **card site** ([online](https://onion-42.github.io/nadja-public-claude-skills/site/),
or open [`site/index.html`](site/index.html) locally) for a filterable view with copy-paste
install commands and a live demo deck: a study deck on self-supervised pathology foundation models
(DINOv2 to Virchow) built with `research-anki-mindmap`. In short:

**Token economy & context**
- `handoff` — package live task state into one resumable doc before a boundary
- `strategic-compact` — decide *when* to compact, and hand off cleanly when you do
- `deep-research` — multi-agent research with citation-traceable output
- `plan-compose` / `plan-reflect` / `plan-archive` — durable, on-disk planning
- `repo-tidy` — surface dead/misplaced files as a reviewable report (proposes, never deletes)
- `time-estimate` — T-shirt sizing to hour ranges with an early drift flag

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

**Study artifacts & reading comfort**
- `anki-mindmap` — the core renderer: one concept graph → an Anki deck (.apkg) + an
  interactive mind-map; reached through two wrappers:
  - `repo-anki-mindmap` — build the graph from a code repository
  - `research-anki-mindmap` — build the graph from papers, notes or a topic
  - cards teach one term each in simple words; `--style nd` makes ADHD/dyslexia/autism-friendly
    cards (OpenDyslexic embedded, wide spacing, optional bionic points)
- `easy-read` — a reading-comfort panel (fonts, spacing, calm colours) for any HTML page

**Evaluation & debate**
- `rag-eval` — evaluate a RAG system with Ragas (faithfulness, retrieval quality)
- `brainstorm` — dialectical debate that **remembers** the discussion across turns

**Subagents** (`plugins/team/agents/`)
- `test-runner` (failures-only, token-frugal), `code-reviewer`, `security-reviewer`,
  `external-researcher`

## ⟐ The `neurodivergent` plugin

Tools that make the output do the remembering. They are offered for comfort and choice; none of
them claims to improve anyone's performance.

- `cho` — "what's going on?": a short status of the current session
- `goal` — pin a dense prompt as a GOAL block and check for drift
- `nopanic` — grounding when overwhelmed (CBT/DBT techniques) plus specific, earned praise
- `when-stuck` — pick a problem-solving technique by the kind of stuck
- `mini-reflection` — a warm three-line end-of-task reflection, written by Claude
- `notify` — one Telegram line when a long task is done or Claude is waiting for you
  (bring your own bot; token from environment variables)
- commands `/checkpoint`, `/pickup-handoff`, `/mode`
- output style `nd-friendly` — answer first, literal language, multiple-choice questions,
  one next action; flags `full`/`short`, `bionic`, `anchor`, `soft`, `literal+` via `/mode`

Already in `team` and useful here too: `handoff`, `roasting`, `step-back`, `time-estimate`,
`easy-read`. Credits for adapted material: [`plugins/neurodivergent/CREDITS.md`](plugins/neurodivergent/CREDITS.md).

## ⟐ Install

In Claude Code:

```
/plugin marketplace add onion-42/nadja-public-claude-skills
/plugin install team@team-claude-skills
/plugin install neurodivergent@team-claude-skills   # optional
```

From a local clone, use `/plugin marketplace add /path/to/clone` instead.

To pick the output style after installing `neurodivergent`: `/config` → Output style → `nd-friendly`.

Or copy individual skills without the plugin system:

```bash
cp -r plugins/team/skills/<name>  ~/.claude/skills/
cp    plugins/team/agents/<name>.md  ~/.claude/agents/
```

Some skills ship a helper script (`agent_bus.py`, `build.py`, `eval_rag.py`); it sits in the
skill's own directory, wherever the skill is installed. Python skills that need a library say so in their SKILL.md
(`genanki`, `markmap`, `ragas`, `boto3`); install only what you use.

## ⟐ Two things you must set yourself

- **`agent-bus` S3 path** — cross-machine sync needs a bucket *your org owns*:
  `export AGENT_BUS_S3="s3://YOUR-BUCKET/YOUR-PREFIX/agent-bus/"`. Unset = local-only, clean
  no-op.
- **`rag-eval` judge model** — Ragas uses an LLM as judge; set it to a model your org
  permits (`RAG_EVAL_PROVIDER` + that vendor's key). The harness refuses to run otherwise,
  so the choice is always explicit.

## ⟐ Testing

The net-new and modified skills (`anki-mindmap` and its two wrappers, `rag-eval`, `brainstorm`,
`agent-bus`, `model-route`, and the `test-runner` agent) are exercised with
`testing-skills-with-subagents`; see [`tests/eval-results/`](tests/eval-results/). Unit tests:
`python -m pytest plugins/team/skills -q`. Adopted skills carry their upstream tests
and are smoke-checked here for valid frontmatter and trigger descriptions.

## ⟐ A note on evidence

The `neurodivergent` plugin and `easy-read` are offered for comfort and choice. Studies of
dyslexia fonts found no reliable gain in reading speed or accuracy (e.g. Wery & Diliberto 2017;
Kuster et al. 2018), and the evidence on bionic-style reading is thin. Some readers find these
settings more comfortable; nothing here claims to improve anyone's performance. `nopanic` is not
therapy and starts with a safety check that points to real help.

## ⟐ See also

Other people's work in the same space (not included here):

- [ravila4/claude-adhd-skills](https://github.com/ravila4/claude-adhd-skills)
- [jpoindexter/nd-skills](https://github.com/jpoindexter/nd-skills)
- [hseinmoussa/exo](https://github.com/hseinmoussa/exo) — output style, MIT
- [assafkip/adhd-output-style](https://github.com/assafkip/adhd-output-style) — output style, MIT
- [alexgreensh/attention-span](https://github.com/alexgreensh/attention-span) — AGPL
- [JackReis/neurodivergent-visual-org](https://github.com/JackReis/neurodivergent-visual-org)
- [thiagoigfraga/active-reading-adhd-audhd](https://github.com/thiagoigfraga/active-reading-adhd-audhd)
- [text-vide](https://github.com/Gumball12/text-vide) — bionic-reading-style text transform

## ⟐ Contributing and licence

Working on the repo (human or agent): read [`AGENTS.md`](AGENTS.md). Changes are listed in
[`CHANGELOG.md`](CHANGELOG.md). MIT licence ([`LICENSE`](LICENSE)); adopted skills that carry their
own licence keep it.
