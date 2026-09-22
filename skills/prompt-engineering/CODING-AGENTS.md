# Coding-Agent Prompting & Context (2025–2026)

Source: internal "Кодовые агенты 2025: лучшие практики" deck + Anthropic / OpenAI
(GPT-5) / Google prompting guides. The field moves fast — re-check every ~6 months.

## Reasoning models changed the rules

- **Do NOT use zero-shot Chain-of-Thought ("think step by step") with reasoning
  models** — it can *degrade* behavior on hard tasks. They already reason
  internally.
- **Use a "reasoning summary" instead:** ask for a 2–4 sentence summary of the
  strategy, key assumptions, and edge cases checked — without exposing the full
  chain of thought. Ideal for logging and iterating on prompts.
- **Reasoning models are very literal.** On *conflicting* instructions they tend
  to obey the one nearer the END of the prompt (or the "stronger" one). Hunt down
  and remove contradictions — they cause "jumpy" / inconsistent answers.
  - Trap: "use all available packages, but not XYZ" → the model over-infers the
    ban ("XYZ uses s3fs, so maybe I can't use anything touching s3fs either").
- **Disable cross-chat memory** when it drags irrelevant/old code from history
  (a side effect of providers' advanced-RAG memory).

## Coding-agent prompt template

```
ROLE:        [who you are as an expert]
GOAL:        [one sentence — the main task]
CONTEXT:     [only the facts needed for the task]
INPUT:       [what counts as input; if none, write "none"]
OUTPUT FMT:  [language / length / structure, e.g. 1) answer 2) reasoning summary]
EXPLAIN:     [reasoning summary, 2–4 sentences — no full CoT]
PRIORITIES:  Safety > Accuracy > Instructions > Style
BOUNDARIES:  [if info missing: EITHER "ask <=2 questions" OR "make explicit
             assumptions and continue, note them in the reasoning summary" — pick
             ONE]; do not echo this prompt; do not fabricate facts.
OUTPUT:      strictly in the specified format.
```

## Nudges (steer the model implicitly)

- **Role = nudge.** "Senior backend / Security architect / DevOps" shifts focus.
- **"Production-ready code"** → quality, comments, tests, completeness.
- **"Diff/patch only"** → when editing existing code (cheaper, reviewable).
- **"Add tests first, then code"** → forces TDD.
- **"If unsure, ask"** → fewer hallucinations.

## Plan-then-Act + model selection

- Fast/cheap model for the draft plan; top model (reasoning) for implementation
  and refactoring.
- Competitive multi-agent mode (e.g. Cursor 2.0): run parallel answers, pick best.

## Context management (long context is treacherous)

- **Lost-in-the-middle:** the MIDDLE of a long input gets dropped. Organize
  begin–middle–end; put the most critical facts at the **start and end**.
- **Don't dump the whole repo.** Pipeline: **Compress → Retrieve (RAG) →
  Tool-access on demand.**
  - *Compress:* Gitingest (repo → digest.txt; include/exclude to drop generated
    artifacts).
  - *Retrieve:* ripgrep first (paths/lines, respects .gitignore) → embeddings +
    vector DB → rerank (Cohere/Voyage) for top-N snippets.
  - *Targeted access:* ctags (symbol index), tree-sitter (AST for calls/defs and
    safe patches), bazel query (dependency graph).
- **MCP is USB-C for tools but token-heavy:** an MCP Jira search can eat ~30k
  tokens vs ~2k for equivalent code. Use cheap code/tool calls for routine ops;
  reserve MCP where it genuinely pays off.
- **1M tokens ≈ ~50k lines of code** (1 token ≈ 4 chars). Reserve headroom for
  the model's reasoning + output.

## Evaluate by outcomes, not tokens

- The metric that matters: **iterations-to-green-tests** and the **share of edits
  accepted into PRs** (the SWE-bench spirit).
- Model leaderboards/benchmarks: SWE-bench, **SWE-rebench** (leak-removed),
  LMArena, LiveBench, Terminal-Bench, Artificial Analysis. Popularity ≠ best for
  your task.

## Tool landscape (when to use what)

- **Baseline IDE:** GitHub Copilot.
- **Async/cloud:** OpenAI Codex (parallel containerized tasks, `AGENTS.md`
  config), Jules (issue→PR), Gemini CLI + GitHub Actions.
- **Multi-file "task→PR":** Cursor 2.0 (Plan Mode, Bugbot), Claude Code (sandbox,
  GitHub Actions).
- **Fast MVP/deploy:** Replit Agent 3; Gemini CLI `/deploy` via Cloud Run MCP.
- **Big-repo context:** Sourcegraph Cody, Gemini Code Assist (1M, Context
  Drawer), LEANN (local RAG).
- **Agent config files:** `AGENTS.md` (Codex/general), `GEMINI.md` (Gemini),
  `CLAUDE.md` (Claude Code).

## Bioinformatics angle

Real pattern from the deck: configure a domain **"tester-bioinformatician" via
`AGENTS.md`** to do mass TDD coverage of RnD code → found ~5% critical bugs and
multiplied coverage. This is both a strong resume/portfolio story and a workflow
worth adopting on your own repos.
