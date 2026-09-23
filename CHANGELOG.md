# Changelog

All notable changes to this marketplace. Versions follow the plugin manifests.

## Unreleased

### Changed
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
