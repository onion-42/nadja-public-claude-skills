# The concept graph (shared by `anki-deck` and `mindmap`)

One JSON graph feeds both renderers: the deck for memorising, the map for seeing how the pieces
connect. A wrapper (`repo-anki-mindmap`, `research-anki-mindmap`) or you build it once; each renderer
only draws it. This file is identical in both skills.

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
  "points": ["Penalizes each vector's closest neighbour", "Helps nearest-neighbour search most"],
  "image": "img/koleo.png"
}
```

- Required: `id` (unique per graph), `title`. Everything else is optional.
- `kind` ∈ `domain` (the problem space) · `method` (a technique) · `concept` (a prerequisite idea).
- `depends_on` builds BOTH the mind-map hierarchy (a node hangs under its prerequisite) and the card
  order (prerequisites first). Keep it a DAG.
- `anchors` = where the claim comes from: `file:line` for code, `arXiv:… §4` / `DOI … Table 2` for
  papers. Source chips on the card back and in the map's details panel.
- `evidence` ∈ `shown` · `plausible` · `guess` · `unverified` (optional; anything else is rejected).
- `group` colours the map branch and fills the legend (the legend names it, so colour is never the
  only cue).
- Cards: `answer` = one plain sentence (about 12 words or fewer); `points` = at most 3, each a few
  words. A node without `answer` falls back to `card_front` / `card_back` (trusted HTML).
- `image` = a picture on the card back, path relative to the graph file and inside its folder
  (png, jpg, gif, webp, svg). Embedded in the `.apkg` under its file name, so names must be unique
  per deck. The map ignores it.
- `summary` = the long, nuanced text for the map's details panel; keep it off the card.

## Guardrails

- **Never fabricate an anchor or a fact.** A card that cites a wrong line or section teaches the
  wrong thing, which is worse than no card. Verify anchors before they reach the graph.
- **One term per card.** If the back needs more than 3 points, split the node.
- **Show the node list before rendering**: pruning a list is cheap, rewriting cards is not.
