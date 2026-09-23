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
  version: "2.1.0"
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
  "id": "koleo",
  "title": "KoLeo regularizer",
  "group": "Methods",
  "kind": "method",
  "depends_on": ["self-distillation"],
  "anchors": ["arXiv:2304.07193 §4"],
  "evidence": "shown",
  "summary": "The full, nuanced explanation lives here: it shows in the mind-map details panel.",
  "answer": "Pushes embeddings in a batch apart from each other.",
  "points": ["Penalizes each vector's closest neighbour", "Helps nearest-neighbour search most"]
}
```

**Cards are term cards by default:** the front is the term (`title`, or `card_front` to override),
the back is one bold `answer` line plus up to 3 short `points`. The old free-text `card_back` (trusted
HTML) still works when a node has no `answer`.

- Required: `id` (unique per graph), `title`. Everything else is optional.
- `kind` ∈ `domain` (the problem space) · `method` (a technique) · `concept` (a prerequisite idea).
- `depends_on` builds BOTH the mind-map hierarchy (a node hangs under its prerequisite) and the card
  order (prerequisites first). Keep it a DAG.
- `anchors` = where the claim comes from: `file:line` for code, `arXiv:… §4` / `DOI … Table 2` for papers.
  They render as `source` chips on the card back and in the map's details panel.
- `evidence` ∈ `shown` · `plausible` · `guess` · `unverified` (optional; anything else is rejected).
- `group` colours the branch and fills the legend.
- `answer` = one plain sentence (about 12 words or fewer); `points` = at most 3, each a few words.

## Writing cards: simple words, one term each

The deck is for **learning terms and concepts**, not for re-reading an analysis.

- One term per card. The front is the term itself, not a long question.
- `answer`: what the thing IS or DOES, in everyday words. No jargon the reader has not had a card for
  yet (prerequisites come first via `depends_on`).
- `points`: the 1-3 facts that make the term stick (what it is for, how it differs, one example).
  Fragments are fine; no nested clauses.
- A number goes on a card only if the number is the point.
- Critique, caveats and "the paper shows vs suggests" nuance go in `summary` (mind-map), not on the card.
  An `unverified` node says so in its first point.

## Render

```bash
python build.py graph.json --deck-name "<Deck name>" --out-dir ./study --source "<repo@commit | topic, date>"
# -> ./study/<deck-name>.apkg, <deck-name>.mindmap.html, <deck-name>.mindmap.md
```

- **Deck id comes from the deck name**, so different decks never merge in Anki. Renaming a deck
  makes a new deck.
- **Styles:** `--style nd` gives ADHD/dyslexia/autism-friendly cards: OpenDyslexic (embedded in the
  `.apkg`, so it works on phones too), one sans stack, no italics, wider line and letter spacing,
  shorter lines, calm colours. OpenDyslexic has Latin letters only; add a font with Cyrillic (or other
  scripts) with `--font-file path.ttf` (repeatable, embedded after OpenDyslexic). `--bionic` bolds the
  first half of each word in `points`. Only embed fonts whose licence allows it. Comfort and choice,
  not a treatment: dyslexia fonts show no reliable reading gains in studies.
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
- **One term per card.** If the back needs more than 3 points, split the node.
- **Degrade, don't fail.** Without genanki you get a TSV (Anki imports it); without the CDN you get the `.md`.
- **Show the node list before rendering** (the wrappers' gate): pruning a list is cheap, rewriting cards is not.

## Files

- `build.py` — graph JSON to `.apkg` + `.mindmap.html` + `.md` (TSV fallback).
- `fonts/` — OpenDyslexic 400/700 woff2 (SIL OFL 1.1, `fonts/OFL.txt`) for `--style nd`.
- `map_template.html` — the mind-map page (design tokens shared with the card CSS in `build.py`).
- `examples/graph.example.json` — a tiny three-node graph; `examples/card-preview.html` — card look.
- `tests/test_build.py` — ids, guids, validation, card chips, map structure, fallbacks.
