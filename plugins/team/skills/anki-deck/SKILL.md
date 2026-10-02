---
name: anki-deck
description: >-
  Render a concept graph (JSON) into an Anki flashcard deck (.apkg): term cards in simple words,
  source chips, evidence levels, optional images, and reading-comfort options from easy-read baked
  into the cards (OpenDyslexic + spacing, bold word starts, colour-vision mode for red-green or
  blue-yellow colour blindness). Usually reached through a wrapper that builds the graph first -
  `repo-anki-mindmap` (code) or `research-anki-mindmap` (papers, notes, a topic). Use it directly
  when a graph already exists or to rebuild / restyle a deck: "render this graph as an Anki deck",
  "rebuild the deck with dyslexia-friendly cards", "колода для дальтоника", "перегенерируй колоду
  из json". For the mind-map of the same graph use `mindmap`.
metadata:
  version: "3.0.0"
  outputs: ".apkg (Anki), or a .tsv when genanki is missing"
  stack: "stdlib + optional genanki"
---

# anki-deck — concept graph → Anki cards

Spaced-repetition **cards** for memorising terms. The expensive step (understanding the source) is
paid once, in whatever builds the graph; this skill only renders it. The node schema, card-writing
rules and guardrails are in **`SCHEMA.md`** next to this file — read it before writing a graph.

## Writing cards: simple words, one term each

- One term per card. The front is the term itself, not a long question.
- `answer`: what the thing IS or DOES, in everyday words. No jargon the reader has not had a card
  for yet (prerequisites come first via `depends_on`).
- `points`: the 1-3 facts that make the term stick. Fragments are fine; no nested clauses.
- A number goes on a card only if the number is the point. Nuance goes in `summary` (the map).
  An `unverified` node says so in its first point.

## Render

```bash
python build_deck.py graph.json --deck-name "<Deck name>" --out-dir ./study
# -> ./study/<deck-name>.apkg   (no genanki -> <deck-name>.tsv, Anki: File > Import)
```

- **Deck id comes from the deck name**, so different decks never merge. Renaming makes a new deck.
- **Card guid comes from (deck name, node id)**: re-importing after an edit updates the card in
  place and keeps its review history. Never reuse an `id` for a different idea.
- Images (`image` in a node) resolve relative to the graph file and are embedded in the `.apkg`.
  They must stay inside the graph's folder, be an image type, and have unique file names — anything
  else is an error, so a stray `../` never packs a private file into a deck you share.

## Reading comfort (the easy-read settings, baked in at build time)

A live panel on every card is unreliable inside Anki, so the `easy-read` settings become build flags:

| easy-read setting | anki-deck |
|---|---|
| Font OpenDyslexic + line / letter spacing + calm colours | `--style nd` (fonts embedded, work on phones) |
| A font with Cyrillic or other scripts | `--font-file path.ttf` (repeatable, after OpenDyslexic) |
| Bold word starts | `--bionic` (in `points`) |
| Colour vision | `--cvd red-green` or `--cvd blue-yellow` (daltonises card colours **and images**) |
| Text size | Anki's own zoom (View → Zoom; phone: Settings) |
| Dark scheme | Anki's night mode (the cards follow it) |

Each style / colour-vision combination is its own Anki note type, so a deck built in one mode never
restyles decks built in another. Card guids stay the same across modes, which has one consequence:
to **switch an already-imported deck** to another mode, either tick *Merge note types* in Anki's
import dialog, or use Browse → select the cards → Notes → Change Note Type; a plain re-import skips
those cards. A fresh deck needs nothing. Colour never carries meaning alone: evidence chips always
show their word (`shown`, `guess`, …).

Comfort and choice, not a treatment: dyslexia fonts show no reliable reading gains in studies, and
daltonisation separates colours that collapse for a reader, it does not restore colour vision. Only
embed fonts whose licence allows it.

## Files

- `build_deck.py` — graph JSON → `.apkg` (TSV fallback); `python build_deck.py -h` for flags.
- `concept_graph.py`, `SCHEMA.md` — the shared graph schema (identical copies live in `mindmap`).
- `fonts/` — OpenDyslexic 400/700 woff2 (SIL OFL 1.1, `fonts/OFL.txt`) for `--style nd`.
- `examples/graph.example.json` — a three-node graph; `examples/card-preview.html` — card look.
- Tests: `python -m pytest tests -q` (from this folder). `tests/test_parity.py` checks the shared
  copies and the colour-vision matrices against siblings when they are installed alongside.
