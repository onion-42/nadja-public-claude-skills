---
name: mindmap
description: >-
  Render a concept graph (JSON) into an interactive, styled mind-map (.html, Markmap) plus a
  portable .md: groups as colour-blind-safe branches with a legend, a details panel with summary,
  sources and evidence, light/dark theme, phone layout, and the easy-read panel (fonts, spacing,
  colour schemes, colour vision, focus highlight) inlined when that skill is installed. Usually
  reached through a wrapper that builds the graph first - `repo-anki-mindmap` (code) or
  `research-anki-mindmap` (papers, notes, a topic). Use it directly when a graph already exists:
  "draw this graph as a mind-map", "rebuild the mind-map", "майндмэп из json". For flashcards of the
  same graph use `anki-deck`.
metadata:
  version: "3.0.0"
  outputs: ".mindmap.html (Markmap) + .mindmap.md (portable)"
  stack: "stdlib; markmap from the jsdelivr CDN at view time"
---

# mindmap — concept graph → interactive mind-map

A **map** for seeing how the pieces connect. The node schema and guardrails are in **`SCHEMA.md`**
next to this file — read it before writing a graph. `depends_on` builds the tree: a node hangs under
its prerequisite.

## Render

```bash
python build_map.py graph.json --title "<Title>" --out-dir ./study --source "<repo@commit | topic, date>"
# -> ./study/<title>.mindmap.html, <title>.mindmap.md
```

## The page

A header (title, concept count, source, legend of groups) and a toolbar (**Fit**, **Expand all**,
**Level 2**, **Theme**; the theme choice is remembered). A click on a node's text opens a details
panel (summary, source chips, evidence), which becomes a bottom sheet on a phone. A click on the
circle folds the branch.

**Colour is never the only cue.** Branch colours come from the Okabe-Ito colour-blind-safe set (each
clears 3:1 against both themes), the legend names every group, and evidence shows as a word.

**easy-read inside:** when the `easy-read` skill is installed next to this one, its "Aa" panel is
inlined, so the reader can switch font, spacing, colour scheme, **colour vision** (red-green /
blue-yellow daltonisation of the whole map) and the focus highlight. Without it the map renders as
designed.

It needs the jsdelivr CDN on first open. If the CDN is blocked (corporate proxy, offline), the page
says so; render the `.md` at markmap.js.org or with a local markmap-cli instead.

## Files

- `build_map.py` — graph JSON → `.mindmap.html` + `.md`.
- `map_template.html` — the page (warm paper design, light/dark).
- `concept_graph.py`, `SCHEMA.md` — the shared graph schema (identical copies live in `anki-deck`).
- `examples/graph.example.json` — a three-node graph.
- Tests: `python -m pytest tests -q` (from this folder).
