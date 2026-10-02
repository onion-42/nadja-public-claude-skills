# Changelog

All notable changes to this marketplace. Versions follow the plugin manifests.

## Unreleased

### Changed
- **`anki-mindmap` is split into two standalone skills**, so each can be installed alone:
  `anki-deck` (graph → `.apkg`, `build_deck.py`) and `mindmap` (graph → `.mindmap.html` + `.md`,
  `build_map.py`). Each ships an identical `concept_graph.py` + `SCHEMA.md`; a parity test guards
  drift. `repo-anki-mindmap` / `research-anki-mindmap` now ask "deck, map or both".
- `mindmap`: branch palette moves to Okabe-Ito colour-blind-safe hues (each ≥ 3:1 on both themes,
  tested); the header counts "concepts" instead of "cards".
- `easy-read` becomes one reading-comfort layer for three surfaces (HTML, mind-map, Anki flags).

### Added
- `easy-read`: **Colour vision** setting — red-green / blue-yellow daltonisation (Machado 2009 +
  Fidaner 2005, one SVG `feColorMatrix`) over the page, charts, images and mind-map, panel excluded.
- `anki-deck --cvd red-green|blue-yellow`: the same daltonisation baked into the cards (own note
  type per mode, guids unchanged), and `image` on a node: a picture on the card back, embedded in
  the `.apkg`.

### Changed (earlier)
- `anki-mindmap`: term cards are the default: the front is the term, the back is one bold `answer`
  line plus up to 3 short `points`. Nuance moves to `summary` (mind-map). Old `card_back` still works.
- The demo deck is rewritten as simple term cards.

### Added
- `anki-mindmap --style nd`: ADHD/dyslexia/autism-friendly cards with OpenDyslexic embedded (SIL OFL,
  `fonts/`), one sans stack, no italics, wider spacing; `--font-file` embeds an extra font (e.g. one
  with Cyrillic); `--bionic` bolds word starts in points.

## 0.1.0 — 2026-09-23

First public release.

### Added
- Plugin marketplace (`.claude-plugin/marketplace.json`) with two plugins:
  - `team` — 30 workflow skills and 4 subagents (planning, debugging, review, research with
    citations, model routing, agent-bus, skill infrastructure).
  - `neurodivergent` — `cho`, `goal`, `nopanic`, `when-stuck`, `mini-reflection`, `notify`,
    commands `/checkpoint`, `/pickup-handoff`, `/mode`, and the `nd-friendly` output style.
- `anki-mindmap` core renderer (concept graph → Anki `.apkg` + interactive mind-map) with two
  wrappers, `repo-anki-mindmap` and `research-anki-mindmap`.
- `easy-read` reading-comfort panel, also inlined into every generated mind-map.
- Card site (`site/index.html`) with a live demo deck on self-supervised pathology foundation
  models.
- `repo-tidy` and `time-estimate` as generic team skills.

### Fixed
- `anki-mindmap`: HTML escaping in the map (XSS), id-keyed node info, cycle detection,
  `ValueError` on malformed graphs.
