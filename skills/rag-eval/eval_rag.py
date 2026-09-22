#!/usr/bin/env python3
"""Evaluate a RAG system with Ragas from a records JSON file.

Records: a JSON list of objects, each:
  {"question": str, "contexts": [str, ...], "answer": str, "ground_truth"?: str}

The judge LLM + embeddings are chosen EXPLICITLY via env and actually WIRED INTO Ragas
(so it never silently falls back to its OpenAI default):
  RAG_EVAL_PROVIDER = openai | azure | anthropic   (the judge vendor)
  RAG_EVAL_MODEL              (optional judge model id override)
  plus that vendor's key env (OPENAI_API_KEY / AZURE_OPENAI_API_KEY / ANTHROPIC_API_KEY)
Anthropic has no embeddings API, so if a metric needs embeddings under an anthropic judge
you must also set RAG_EVAL_EMBEDDINGS_PROVIDER = openai | azure.

Prints per-metric means and per-metric worst rows, writes a full CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

METRIC_NEEDS_GT = {"context_recall"}
METRIC_NEEDS_EMB = {"answer_relevancy", "context_precision", "context_recall"}
_KEYMAP = {"openai": "OPENAI_API_KEY", "azure": "AZURE_OPENAI_API_KEY",
           "anthropic": "ANTHROPIC_API_KEY"}


def die(msg: str) -> None:
    sys.exit("ERROR: " + msg)


def load_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        die("records JSON must be a non-empty list.")
    for i, r in enumerate(data):
        for f in ("question", "contexts", "answer"):
            if f not in r or (isinstance(r[f], str) and not r[f].strip()):
                die(f"record {i}: field '{f}' is missing or empty.")
        if not isinstance(r["contexts"], list) or not r["contexts"]:
            die(f"record {i}: 'contexts' must be a non-empty list of strings.")
        if any(not isinstance(c, str) or not c.strip() for c in r["contexts"]):
            die(f"record {i}: every 'contexts' element must be a non-empty string.")
    return data


def require_judge() -> str:
    provider = os.environ.get("RAG_EVAL_PROVIDER", "").strip().lower()
    if not provider:
        die("RAG_EVAL_PROVIDER is unset. Set it to an APPROVED vendor "
            "(openai | azure | anthropic) plus that vendor's key env. "
            "Refusing to fall through to an unvetted default judge model.")
    if provider not in _KEYMAP:
        die(f"RAG_EVAL_PROVIDER='{provider}' not recognised (openai|azure|anthropic).")
    if not os.environ.get(_KEYMAP[provider]):
        die(f"provider '{provider}' selected but {_KEYMAP[provider]} is not set.")
    return provider


def _embeddings(provider: str):
    """Return a langchain embeddings client for openai|azure, or die."""
    try:
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model=os.environ.get("RAG_EVAL_EMBED_MODEL", "text-embedding-3-small"))
        from langchain_openai import AzureOpenAIEmbeddings
        return AzureOpenAIEmbeddings(azure_deployment=os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT"))
    except ImportError:
        die("langchain-openai not installed. `pip install langchain-openai`.")


def build_judge(provider: str, needs_embeddings: bool):
    """Construct (llm, embeddings) wrapped for Ragas from the chosen provider.
    NEVER returns Ragas's implicit default — an unbuildable judge dies loudly."""
    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
    except ImportError:
        die("ragas not installed. `pip install ragas datasets`.")

    model = os.environ.get("RAG_EVAL_MODEL")
    emb = None
    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model or "gpt-4o-mini", temperature=0)
            if needs_embeddings:
                emb = _embeddings("openai")
        elif provider == "azure":
            from langchain_openai import AzureChatOpenAI
            dep = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or model
            if not dep:
                die("azure judge needs AZURE_OPENAI_DEPLOYMENT (or RAG_EVAL_MODEL).")
            llm = AzureChatOpenAI(azure_deployment=dep, temperature=0)
            if needs_embeddings:
                emb = _embeddings("azure")
        else:  # anthropic
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model or "claude-3-5-sonnet-latest", temperature=0)
            if needs_embeddings:
                ep = os.environ.get("RAG_EVAL_EMBEDDINGS_PROVIDER", "").strip().lower()
                if ep not in ("openai", "azure"):
                    die("anthropic judge selected and a metric needs embeddings, but "
                        "Anthropic has no embeddings API. Set RAG_EVAL_EMBEDDINGS_PROVIDER"
                        "=openai|azure (with that vendor's key).")
                emb = _embeddings(ep)
    except ImportError:
        pkg = "langchain-anthropic" if provider == "anthropic" else "langchain-openai"
        die(f"{pkg} not installed. `pip install {pkg}`.")

    return LangchainLLMWrapper(llm), (LangchainEmbeddingsWrapper(emb) if emb is not None else None)


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG eval via Ragas (explicit, wired judge)")
    ap.add_argument("records", type=Path)
    ap.add_argument("--metrics", default="faithfulness,answer_relevancy",
                    help="comma list: faithfulness,answer_relevancy,context_precision,context_recall")
    ap.add_argument("--out-csv", type=Path, default=Path("rag_eval_results.csv"))
    ap.add_argument("--worst", type=int, default=5)
    args = ap.parse_args()

    records = load_records(args.records)
    provider = require_judge()
    wanted = [m.strip() for m in args.metrics.split(",") if m.strip()]

    needs_gt = [m for m in wanted if m in METRIC_NEEDS_GT]
    if needs_gt and any(not str(r.get("ground_truth", "")).strip() for r in records):
        die(f"metric(s) {needs_gt} need a non-empty 'ground_truth' on every record.")

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas import metrics as M
    except ImportError:
        die("ragas + datasets not installed. `pip install ragas datasets`.")

    metric_objs = []
    for m in wanted:
        obj = getattr(M, m, None)
        if obj is None:
            die(f"unknown Ragas metric '{m}'.")
        metric_objs.append(obj)

    needs_emb = bool(set(wanted) & METRIC_NEEDS_EMB)
    judge_llm, judge_emb = build_judge(provider, needs_emb)

    ds = Dataset.from_list([
        {"question": r["question"], "contexts": r["contexts"], "answer": r["answer"],
         **({"ground_truth": r["ground_truth"]} if "ground_truth" in r else {})}
        for r in records
    ])

    print(f"Judging with provider={provider}"
          + (f", model={os.environ.get('RAG_EVAL_MODEL')}" if os.environ.get("RAG_EVAL_MODEL") else "")
          + f", {len(records)} records, metrics={wanted}")
    # Wire the chosen judge in explicitly — do NOT let Ragas pick a default.
    kwargs = {"llm": judge_llm}
    if judge_emb is not None:
        kwargs["embeddings"] = judge_emb
    result = evaluate(ds, metrics=metric_objs, **kwargs)
    df = result.to_pandas()

    print("\n=== Means ===")
    for m in wanted:
        if m in df.columns:
            print(f"  {m:20s} {df[m].mean():.3f}")

    # Worst rows PER METRIC — a low mean on one metric must surface ITS worst rows,
    # not be hidden behind the first metric's ranking.
    for m in wanted:
        if m in df.columns:
            print(f"\n=== Worst {args.worst} rows by {m} ===")
            for _, row in df.nsmallest(args.worst, m).iterrows():
                print(f"  [{m}={row[m]:.2f}] Q: {str(row['question'])[:88]}")

    df.to_csv(args.out_csv, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"\nFull results -> {args.out_csv}")


if __name__ == "__main__":
    main()
