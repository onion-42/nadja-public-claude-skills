---
name: anki-mindmap
description: >-
  Core renderer for study artifacts: turns ONE concept graph (JSON) into an Anki flashcard deck
  (.apkg) and an interactive, styled mind-map (HTML). Holds the graph schema, the shared design
  and the honesty rules. Usually reached through a wrapper that builds the graph first -
  `repo-anki-mindmap` (from a code repository) or `research-anki-mindmap` (from papers, notes or a
  topic). Use it directly when a concept graph already exists, or to re-render / restyle a deck:
  "render this graph as an Anki deck", "rebuild the mind-map", "перегенерируй колоду из json".
metadata:
  version: "2.0.0"
  outputs: ".apkg (Anki) + .mindmap.html (Markmap) + .mindmap.md (portable)"
  stack: "stdlib + optional genanki; markmap from the jsdelivr CDN at view time"
---

# anki-mindmap (core)

One graph, two artifacts: spaced-repetition **cards** for memorising and a **mind-map** for seeing how
the pieces connect. The expensive step (understanding the source) is paid once, in the wrapper that
builds the graph; this skill only renders it.

## The concept graph (shared source of truth)

A JSON list of nodes (or `{"nodes": [...]}`):

```json
{
  "id": "concat-pooling",
  "title": "CLS ‖ mean concat",
  "group": "Methods",
  "kind": "method",
  "depends_on": ["cls-token", "mean-pooling"],
  "anchors": ["arXiv:2304.07193 §4"],
  "evidence": "shown",
  "summary": "One paragraph, grounded in the anchors.",
  "card_front": "Why concatenate the CLS token with mean-pooled patch tokens?",
  "card_back": "2-4 sentences answering exactly that question."
}
```

- Required: `id` (unique per graph), `title`. Everything else is optional.
- `kind` ∈ `domain` (the problem space) · `method` (a technique) · `concept` (a prerequisite idea).
- `depends_on` builds BOTH the mind-map hierarchy (a node hangs under its prerequisite) and the card
  order (prerequisites first). Keep it a DAG.
- `anchors` = where the claim comes from: `file:line` for code, `arXiv:… §4` / `DOI … Table 2` for papers.
  They render as `source` chips on the card back and in the map's details panel.
- `evidence` ∈ `shown` · `plausible` · `guess` · `unverified` (optional; anything else is rejected).
- `group` colours the branch and fills the legend.

## Render

```bash
python build.py graph.json --deck-name "<Deck name>" --out-dir ./study --source "<repo@commit | topic, date>"
# -> ./study/<deck-name>.apkg, <deck-name>.mindmap.html, <deck-name>.mindmap.md
```

- **Deck id comes from the deck name**, so different decks never merge in Anki. Renaming a deck
  makes a new deck.
- **Card guid comes from (deck name, node id)**, so re-importing after editing a card's text updates
  it in place and keeps its review history. Never reuse an `id` for a different idea.
- Tests: `python -m pytest tests -q` (from this folder).

## The mind-map

A header (title, card count, source, legend of groups) and a toolbar (**Fit**, **Expand all**,
**Level 2**, **Theme**; the theme choice is remembered). A click on a node's text opens a details
panel (summary, source chips, evidence), which becomes a bottom sheet on a phone. A click on the
circle folds the branch. It has light and dark themes and works at phone width.

It needs the jsdelivr CDN on first open. If the CDN is blocked (corporate proxy, offline), the page
says so; render the `.md` next to it at markmap.js.org or with a local markmap-cli instead.

## Guardrails

- **Never fabricate an anchor or a fact.** A card that cites a wrong line or section teaches the
  wrong thing, which is worse than no card. The wrapper verifies anchors before they reach the graph.
- **One idea per card.** If `card_back` needs three facts, split the node.
- **Degrade, don't fail.** Without genanki you get a TSV (Anki imports it); without the CDN you get the `.md`.
- **Show the node list before rendering** (the wrappers' gate): pruning a list is cheap, rewriting cards is not.

## Files

- `build.py` — graph JSON to `.apkg` + `.mindmap.html` + `.md` (TSV fallback).
- `map_template.html` — the mind-map page (design tokens shared with the card CSS in `build.py`).
- `examples/graph.example.json` — a tiny three-node graph; `examples/card-preview.html` — card look.
- `tests/test_build.py` — ids, guids, validation, card chips, map structure, fallbacks.
