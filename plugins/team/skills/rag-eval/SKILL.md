---
name: rag-eval
description: >-
  Evaluate a Retrieval-Augmented Generation (RAG) system with Ragas — measure whether
  answers are faithful to the retrieved context and whether retrieval actually surfaced
  the right passages, without needing hand-labelled ground truth. Use when someone asks
  to "test our RAG", "check if the chatbot is hallucinating", "measure retrieval quality",
  "is the answer grounded in the docs", "score our retriever", or is about to ship / change
  a retrieval or prompt and wants a regression number. Not for evaluating a plain LLM with
  no retrieval step — this is specifically for the retrieve-then-generate loop.
metadata:
  version: "1.0.0"
  framework: "Ragas (reference-free RAG metrics)"
  upgrade_path: "DeepEval for pytest/CI gating"
---

# rag-eval

A RAG system fails in two distinct places, and a single "does the answer look good"
glance hides which one. This skill separates them:

- **Generation faithfulness** — is the answer actually supported by the retrieved
  context, or did the model invent it? (This is the hallucination metric.)
- **Retrieval quality** — did the retriever surface the passages that were needed?
  A perfectly faithful answer to bad context is still a bad system.

Ragas measures both, and its core metrics are **reference-free** — you do not need a
gold answer for every question, only the (question, retrieved contexts, answer) triple
the system already produces. That is what makes it the lightest thing to wire in.

## The metrics (what each one catches)

| Metric | Needs ground truth? | Catches |
|---|---|---|
| `faithfulness` | no | answer claims NOT entailed by the retrieved context (hallucination) |
| `answer_relevancy` | no | answers that are off-topic or evasive for the question |
| `context_precision` | ranking only | relevant passages buried below noise in the retrieved set |
| `context_recall` | **yes** (gold answer) | needed information the retriever missed entirely |

Run the first two always. Add the context metrics when you have a small labelled set —
even 20-50 gold examples is enough for a meaningful retrieval number.

## The hard constraint: pick an approved judge model

Ragas uses an **LLM as the judge** and (for retrieval metrics) an embedding model. Left
alone it silently defaults to OpenAI. The harness closes that hole: it **constructs the
judge from your env and passes it into `evaluate(llm=, embeddings=)`** — Ragas never picks
a default. If the judge can't be built, it dies loudly rather than falling through.

Set, per run:
- `RAG_EVAL_PROVIDER = openai | azure | anthropic` + that vendor's key env
  (`OPENAI_API_KEY` / `AZURE_OPENAI_API_KEY` / `ANTHROPIC_API_KEY`).
- `RAG_EVAL_MODEL` (optional) — override the judge model id.
- **Anthropic has no embeddings API.** If a metric needs embeddings (`answer_relevancy`,
  `context_precision`, `context_recall`) under an anthropic judge, also set
  `RAG_EVAL_EMBEDDINGS_PROVIDER = openai | azure`. Faithfulness alone needs no embeddings.

For a team with data-residency or vendor rules, this wiring is what keeps evaluation itself
compliant — the judge is exactly the model you named, never an implicit fallback.

## Procedure

1. **Get the data as records** — a JSON list of
   `{"question", "contexts": [...], "answer", "ground_truth"?}`. If the RAG system is
   live, run it over a question set first and capture those four fields per question.
2. **Choose metrics** by what data you have (table above). No ground truth -> faithfulness
   + answer_relevancy only.
3. **Set the judge** (see above) and run the bundled harness:

```bash
pip install ragas datasets
python eval_rag.py records.json --metrics faithfulness,answer_relevancy
# with a labelled set:
python eval_rag.py records.json --metrics faithfulness,answer_relevancy,context_precision,context_recall
```

4. **Read per-metric means AND the worst rows.** The mean tells you if it regressed; the
   worst 5 rows tell you *why*. The harness prints both and writes a full CSV.
5. **Report** the numbers with their meaning ("faithfulness 0.72 = ~28% of answers make a
   claim the context does not support"), not just the digits.

## Guardrails

- **A number without the failing examples is theatre.** Always surface the worst rows;
  that is where the fix is. The mean alone cannot be acted on.
- **Small and labelled beats large and unlabelled for retrieval.** Do not skip
  context_recall because labelling is tedious — 30 gold rows answer "is the retriever the
  problem?" definitively.
- **Judge model drift changes scores.** Pin the judge model + version in the report so two
  runs are comparable. A score is only a regression signal against the same judge.
- **Reference-free is not assumption-free.** Faithfulness trusts that the retrieved context
  is what the model actually saw — verify the records capture the REAL context passed to the
  generator, not a re-fetch.

## Upgrade path

When the team wants eval to run in CI as pass/fail gates (`assert_test`), port the same
records to **DeepEval** — it wraps these metrics with pytest integration and thresholds.
Ragas is the fast local read; DeepEval is the gate. Same records feed both.

## Files

- `SKILL.md` — this recipe.
- `eval_rag.py` — records JSON -> Ragas metrics, prints means + worst rows, writes CSV.
- `examples/records.example.json` — three records to smoke-test the harness shape.
