---
name: research-anki-mindmap
description: >-
  Turn papers, research notes or a topic into study material: an Anki flashcard deck (.apkg) and
  an interactive mind-map, built from one concept graph where every claim cites the source it came
  from and carries an evidence level. Use when someone wants to LEARN a research area or keep what
  they read — "flashcards from these papers", "Anki deck from my research notes", "mind-map of this
  topic", "карточки по статьям", "анки по рисёчу", "майндмэп по теме". Inputs can be a notes file,
  DOIs/arXiv ids, PDFs, a Zotero collection or just a topic. For a code repository use
  `repo-anki-mindmap`.
metadata:
  version: "2.0.0"
  requires: "anki-deck (cards) and/or mindmap (map); easy-read optional"
---

# research-anki-mindmap (wrapper: sources → concept graph)

This skill does **Stage 0 for research**: gather and read the sources, then build the concept graph.
Rendering lives in two standalone skills: **`anki-deck`** (cards) and **`mindmap`** (map). The node
schema and guardrails are in `SCHEMA.md` inside either of them; read it before writing the graph.

## Gate 1 — scope, audience, sources, output (ask if missing)

- **Scope + audience** in one line (e.g. *"pooling strategies for frozen ViT embeddings, for an ML
  engineer who knows transformers"*). The audience caps depth.
- **Output: deck, map, or both** (default both), and whether the reader wants reading comfort
  (dyslexia-friendly cards, colour-blind mode).
- **Sources**, in order of preference:
  1. what the user gives: a notes file / research.md, DOIs, arXiv ids, PDFs, a Zotero collection
     (only if a Zotero MCP is available);
  2. only a topic → find sources: a literature agent such as `robin` **if one is available**,
     otherwise WebSearch + WebFetch. Prefer primary papers and reviews over blog posts.

## Stage 0 — build the graph from sources

1. **Papers are anchors, not nodes.** Nodes stay ideas (`domain` / `method` / `concept`); each node's
   `anchors` cite where its claim comes from: `arXiv:2304.07193 §4`, `DOI 10.1038/… Fig. 3`,
   `notes.md §5`.
2. **Evidence ladder** on every node that makes a claim:
   - `shown` — the opened source states or demonstrates it;
   - `plausible` — follows from the sources but is not stated;
   - `guess` — an informed hypothesis;
   - `unverified` — only the abstract or a secondary mention was read.
3. **Honesty rule (mirror of the code rule):** anchor only what was actually opened. Never invent a DOI,
   section, table or number. If a source could not be opened, keep the node but mark it `unverified`
   and say so in the node's first `points` entry.
4. **Cards teach terms in simple words** (`anki-deck` SKILL.md, "Writing cards"): front = the term,
   `answer` = one plain sentence, `points` ≤ 3 short facts. The "paper shows vs suggests" nuance,
   numbers and critique go in `summary`, which the mind-map shows; keep them off the card.
5. Write the graph to `_ram_graph.json`.

## Gate 2 — approve the node list, then render

Show node titles + groups + evidence; let the user prune/add. Then render what Gate 1 asked for:

```bash
# deck   (add --style nd [--bionic] [--cvd red-green|blue-yellow] if asked)
python <skills-dir>/anki-deck/build_deck.py _ram_graph.json --deck-name "<Topic>" --out-dir ./study
# map    (easy-read panel is inlined automatically when that skill is installed)
python <skills-dir>/mindmap/build_map.py _ram_graph.json --title "<Topic>" \
  --out-dir ./study --source "<topic>, <YYYY-MM-DD>"
```

Report the card count, how many nodes are `unverified`, how to import the `.apkg`, and that the map
needs the CDN on first open (the `.md` is the fallback). A renderer skill that is not installed →
say which one to install instead of failing silently.
