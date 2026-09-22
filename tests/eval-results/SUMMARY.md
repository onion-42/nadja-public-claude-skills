# Skill eval — testing-skills-with-subagents

**Date:** 2026-09-22 · **Method:** one adversarial subagent per skill (Opus, low/medium
effort). Each read the skill, ran the real scenario (executing bundled scripts where
present), judged acceptance criteria strictly, and hunted for loopholes — ways to follow
the letter of the skill and still do the wrong thing.

**Result: 6 / 6 passed.** Every criterion met with evidence. The adversarial pass surfaced
real defects, which were then fixed (below).

## Fixes applied after the eval

| Skill | Defect found | Fix |
|---|---|---|
| **rag-eval** | **CRITICAL** — the judge gate was decorative: `RAG_EVAL_PROVIDER` was checked but never passed to Ragas, so it silently used its OpenAI default regardless of the approved vendor. | `build_judge()` now constructs the provider's LLM (+ embeddings) and passes them to `evaluate(llm=, embeddings=)`; an unbuildable judge dies loudly. Anthropic (no embeddings API) requires `RAG_EVAL_EMBEDDINGS_PROVIDER`. |
| **rag-eval** | Worst rows ranked only by the first metric — could hide the worst hallucinations behind another metric's ranking. | Worst rows now printed **per metric**. |
| **rag-eval** | Record validation accepted empty `contexts`/`ground_truth`. | Rejects empty strings and empty/non-string `contexts`. |
| **repo-anki-mindmap** | SKILL claimed the mind-map HTML "works offline"; it actually loads markmap from a CDN at view time. Stale `npx markmap-cli` wording. | SKILL + `build.py` stdout corrected: HTML needs the CDN on first open; `.md` is the portable fallback. npx wording removed (build uses the CDN autoloader). |
| **brainstorm** | The debate-log read/write was pure honor-system — an agent could claim compliance without touching the log; slug drift orphaned history. | SKILL now requires printing the resolved slug + log path and echoing the prior `State:` line (or "no prior log"), and mandates slug reuse. |
| **agent-bus** | `post --refs X` succeeded even when X didn't exist; `F:/agent-bus-archive` was a baked Windows-drive default. | `cmd_post` warns (non-fatal) on a missing `--refs` file; archive default is now `~/.agent-bus-archive`. |
| **model-route** | Baseline tier was never anchored (an agent could set the top tier as baseline for everything); "extract" example ambiguous. | SKILL anchors a constant mid baseline tier ("only effort moves") and splits mechanical string-extraction from comprehension-extraction. |

## Accepted limitations (intrinsic to behavioral skills — not fixed by design)

Process-doc skills can be *nudged* toward observability but not *enforced* by code without
over-engineering (KISS). These remain the caller's responsibility:

- `brainstorm` persona opposition and `model-route` routing are behavioral — a determined
  agent can stage compliance. The skills raise the cost of doing so (bias flags, visible
  log reads, anchored baseline) but cannot guarantee good faith.
- `agent-bus` claims dedup and file-first handoff are conventions the CLI now *warns* about
  but does not hard-block; cross-machine `--refs` files still need a separate `aws s3 cp`.
- `repo-anki-mindmap` code-anchor honesty is a guardrail instruction, not a tooling gate
  (`build.py` emits whatever anchors the graph contains). Grep anchors before shipping.

## Re-verification after fixes

- `rag-eval`: refuses with no `RAG_EVAL_PROVIDER` (exit 1); rejects empty `contexts` (exit 1);
  reaches the wired judge path. ✅
- `repo-anki-mindmap`: `build.py` on the example graph produces `.apkg` (native genanki) +
  themed mind-map HTML + `.md`; degrades to TSV when genanki is absent. ✅
- `agent-bus`: `--refs` warning fires on a missing file; archive default resolves to
  `~/.agent-bus-archive`; `sync` is a clean no-op with `AGENT_BUS_S3` unset. ✅
