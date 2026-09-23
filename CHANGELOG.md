# Changelog

All notable changes to this marketplace. Versions follow the plugin manifests.

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
