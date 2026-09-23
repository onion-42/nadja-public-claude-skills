---
name: repo-anki-mindmap
description: >-
  Turn a code repository (or a subsystem of one) into study material: an Anki flashcard deck
  (.apkg) and an interactive mind-map, built from one concept graph of the code. Use when someone
  wants to LEARN or ONBOARD onto a codebase fast — "make me flashcards for this repo", "build an
  Anki deck from this pipeline", "give me a mind-map of how this service fits together", "карточки
  по репо", "майндмэп по коду". Not for a one-off walkthrough: use it when the output is durable
  study material someone will keep reusing. For papers, notes or a topic use `research-anki-mindmap`.
metadata:
  version: "2.0.0"
  requires: "anki-mindmap (core renderer)"
---

# repo-anki-mindmap (wrapper: code → concept graph)

This skill does **Stage 0 for code**: read the repo and build the concept graph. The rendering,
schema, design and guardrails live in the core skill **`anki-mindmap`**; read its SKILL.md for the
node schema before writing the graph.

## Gate 1 — scope + audience (ask if missing)

One line: which repo/subsystem, and who the learner is (e.g. *"a new hire fluent in Python, new to
our embedding pipeline"*). The audience caps how deep the graph goes: stop recursing into concepts
the learner already knows. No scope → ask one multiple-choice question.

## Stage 0 — build the graph from code

1. Read the code (Grep/Read; for notebooks read cells, not raw JSON). Name three kinds of node:
   the **domain** (what problem the code solves), the **methods** (techniques in the code) and the
   **concepts** (prerequisite ideas needed to follow a method).
2. Method nodes carry `anchors` as `file:line` that **actually exist**: grep each one before it
   goes in. Pure-concept nodes carry none.
3. Pin the commit: pass `--source "<repo>@<short-sha>"`, so the anchors stay meaningful.
4. `evidence` is usually unnecessary for code (the anchor is the evidence). Use `unverified` for a
   claim about behaviour you inferred but did not run or trace.
5. **Cards teach terms in simple words** (core SKILL.md, "Writing cards"): front = the term
   (a module, class or idea), `answer` = one plain sentence of what it does, `points` ≤ 3 short
   facts (where it lives, what calls it). Details go in `summary`.
6. Write the graph to `_ram_graph.json`.

## Gate 2 — approve the node list, then render

Show node titles + groups; let the user prune/add. Then render with the core:

```bash
python <skills-dir>/anki-mindmap/build.py _ram_graph.json --deck-name "Repo: <name>" \
  --out-dir ./study --source "<repo>@<sha>"   # add --style nd [--bionic] if asked
```

Report the card count, how to import the `.apkg` (Anki, File, Import), and that the map needs the CDN
on first open (the `.md` is the fallback).
