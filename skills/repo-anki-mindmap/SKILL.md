---
name: repo-anki-mindmap
description: >-
  Turn a code repository (or a subsystem of one) into two study artifacts from a
  single shared concept graph: an Anki flashcard deck (.apkg) and an interactive
  mind-map (HTML, via Markmap). Use when someone wants to LEARN or ONBOARD onto a
  codebase fast — "make me flashcards for this repo", "build an Anki deck from this
  pipeline", "give me a mind-map of how this service fits together", "help me revise
  this module before the interview". Not for a one-off code walkthrough — use it when
  the output is durable study material a person (or a team) will keep reusing.
metadata:
  version: "1.0.0"
  outputs: ".apkg (Anki) + .html (Markmap mind-map)"
  stack: "stdlib graph build + genanki + markmap-cli"
---

# repo-anki-mindmap

One extraction, two artifacts. You read the repo once, build a **concept graph**
(the same structure that powers a good explainer), and then render it two ways:
spaced-repetition **flashcards** for memorising, and a **mind-map** for seeing how
the pieces connect. Doing both from one graph is the whole point — the expensive
step (understanding the code) is paid once.

## Two gates (do not skip)

1. **Scope + audience, stated per run.** Get one line: which repo/subsystem, and who
   the learner is (e.g. *"a new hire fluent in Python, new to our embedding pipeline"*).
   This bounds how deep the graph goes and how hard the cards are. No scope → ask.
2. **Graph approval before rendering.** Building the graph is cheap; rendering and
   card-writing is not. Show the node list and let the user prune/add before you
   generate the deck and map. A wrong-scope guess dies here, cheaply.

## The concept graph (the shared source of truth)

Write `_ram_graph.json` — a list of nodes, each:

```json
{
  "id": "embed-pipeline",
  "title": "Embedding pipeline",
  "group": "Architecture",
  "kind": "method",
  "depends_on": ["tokenizer", "model-loader"],
  "has_code": true,
  "anchors": ["src/embed/pipeline.py:40"],
  "summary": "One-paragraph explanation grounded in the code above.",
  "card_front": "What does the embedding pipeline do, end to end?",
  "card_back": "It ... (2-4 sentences). Entry point: src/embed/pipeline.py:40."
}
```

Rules that keep it honest:
- `kind` is one of `domain` (the problem space), `method` (a technique in the code),
  or `concept` (a prerequisite idea needed to understand a method).
- `has_code:true` nodes carry verified `anchors` (`file:line` that actually exist —
  grep them, do not invent them). Pure-concept nodes carry none.
- `depends_on` is what builds the mind-map hierarchy AND the card ordering (teach
  prerequisites first). Keep it a DAG; if you create a cycle, you mis-modelled it.
- `card_front`/`card_back` are the flashcard. Front = one question. Back = the answer
  in the learner's language, ending with the code anchor when there is one.
- Cap depth at the audience baseline — stop recursing into concepts the learner
  already knows.

## Procedure

1. **Read the repo** (Grep/Read; for notebooks read cells, not raw JSON). Identify
   the domain, the methods in the code, and the prerequisite concepts. Build the
   graph and write it to `_ram_graph.json`.
2. **Gate 2** — show the node titles + groups, get approval / edits.
3. **Render both artifacts** with the bundled script:

```bash
python build.py _ram_graph.json --deck-name "Repo: <name>" --out-dir ./study
# writes ./study/<name>.apkg  and  ./study/<name>.mindmap.html
```

4. **Verify before handing over:** open the `.html` **with a network connection** (it
   fetches markmap from the CDN on first view, then shows the tree), and report the card
   count from the script's stdout. Tell the user how to import the `.apkg` (Anki, File,
   Import), and that the `.html` needs the CDN on first open — the `.md` is the portable
   fallback for markmap.js.org or a local markmap.

## The stack (why these)

- **`genanki`** builds a real `.apkg` directly in Python — no running Anki instance
  needed. Stable deck/model ids (baked into the script) mean re-running updates the
  same deck instead of duplicating it. `pip install genanki`.
- **`markmap`** turns a nested Markdown outline into an interactive, zoomable,
  collapsible mind-map. The script emits the outline from `depends_on` and writes a single
  HTML file that loads markmap from the jsdelivr CDN **at view time** — so there is no
  `npm`/`npx` install at build (corporate TLS proxies choke on runtime `npx`). It also
  writes a portable `.md` you can render at markmap.js.org or with a locally installed
  markmap. **Network note:** the HTML needs to reach the CDN the first time it is opened;
  it is not an offline artifact. If you need a truly offline map, render the `.md` with a
  locally installed `markmap-cli` and ship that output.

## Guardrails

- **Never fabricate a code anchor or a fact.** A card that cites `foo.py:120` when
  that line is something else teaches the wrong thing — worse than no card. Grep every
  anchor before it goes in the graph.
- **One idea per card.** If `card_back` needs three separate facts, split the node.
  Spaced repetition breaks on multi-fact cards.
- **Cheap fallback beats a hard dependency.** If `genanki`/`markmap` aren't installed,
  the script still writes the deck as a TSV (Anki imports TSV) and the map as `.md`
  for markmap.js.org — degrade, don't fail.
- **Keep it a DAG.** The mind-map and card ordering both assume prerequisites resolve;
  a cycle silently corrupts both.

## Files

- `SKILL.md` — this recipe.
- `build.py` — graph JSON to `.apkg` + `.mindmap.html` (with TSV/`.md` fallbacks).
- `examples/graph.example.json` — a tiny three-node graph to test the renderer.
