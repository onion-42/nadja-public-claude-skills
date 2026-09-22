#!/usr/bin/env python3
"""Render a concept-graph JSON into an Anki deck (.apkg) and a Markmap mind-map (.html).

Input graph: a JSON list of nodes, each with at least {id, title, card_front,
card_back} and optionally {group, depends_on, anchors, summary}. See SKILL.md.

Degrades instead of failing:
- no genanki installed -> writes a TSV Anki can import (File > Import).
- no markmap-cli/npx    -> writes a .md the user drops at https://markmap.js.org.

KISS: stdlib + optional genanki. No network, no config.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Stable ids so re-running UPDATES the same deck/model instead of duplicating.
DECK_ID = 1607392319
MODEL_ID = 1091735104

# --- Shared "Warm study / paper" design system (site + Anki + mind-map) ---
# Muted branch palette for the mind-map, ordered for readable adjacency.
MAP_BRANCH_COLORS = ["#b0603f", "#5a7d6f", "#c08a2d", "#6b7f9e", "#8c5a6e", "#7a8a5a"]

# Anki card face CSS. Phone-first, warm cream, high contrast, dark-mode aware
# (Anki adds .night_mode / .card.nightMode). Baked into the genanki Model so a
# .apkg ships its own styling with no per-user setup.
ANKI_CSS = """
.card {
  --paper: #faf6ef; --surface: #fffdf8; --ink: #2b2622; --ink-soft: #6b6259;
  --accent: #b0603f; --code-bg: #f0e9dd; --border: #e5dccb;
  font-family: -apple-system, "Segoe UI", "Inter", system-ui, sans-serif;
  font-size: 22px; line-height: 1.6; color: var(--ink);
  background: var(--paper); text-align: left;
  padding: 28px 22px; max-width: 44rem; margin: 0 auto;
}
.q {
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  font-size: 1.28em; font-weight: 600; line-height: 1.35;
  color: var(--ink); margin: 0 0 4px;
}
hr#answer {
  border: 0; height: 1px; background: var(--accent); opacity: .5;
  margin: 20px 0; }
.a { font-size: 1em; color: var(--ink); }
.a code, .anchor {
  font-family: "SF Mono", "JetBrains Mono", ui-monospace, Menlo, monospace;
  font-size: .82em; background: var(--code-bg); color: var(--accent);
  padding: 2px 7px; border-radius: 6px; border: 1px solid var(--border);
  white-space: nowrap; }
.anchor { display: inline-block; margin-top: 14px; }
.night_mode .card, .card.nightMode {
  --paper: #211d1a; --surface: #2a2521; --ink: #efe7db; --ink-soft: #b6ab9c;
  --accent: #e08a63; --code-bg: #2f2823; --border: #3d352d; }
"""


def _anki_front(front: str) -> str:
    return f'<div class="q">{front}</div>'


def _anki_back(back: str) -> str:
    return f'<div class="a">{back}</div>'


def load_graph(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "nodes" in data:
        data = data["nodes"]
    if not isinstance(data, list):
        sys.exit("ERROR: graph JSON must be a list of nodes (or {'nodes': [...]}).")
    for i, n in enumerate(data):
        if not isinstance(n, dict) or "id" not in n or "title" not in n:
            sys.exit(f"ERROR: node {i} missing required 'id'/'title'.")
    return data


def topo_order(nodes: list[dict]) -> list[dict]:
    """Prerequisites first. Falls back to input order on a cycle (and warns)."""
    by_id = {n["id"]: n for n in nodes}
    visited: dict[str, int] = {}  # 0=visiting, 1=done
    out: list[dict] = []
    cycle = False

    def visit(nid: str) -> None:
        nonlocal cycle
        state = visited.get(nid)
        if state == 1:
            return
        if state == 0:
            cycle = True
            return
        visited[nid] = 0
        for dep in by_id.get(nid, {}).get("depends_on", []) or []:
            if dep in by_id:
                visit(dep)
        visited[nid] = 1
        out.append(by_id[nid])

    for n in nodes:
        visit(n["id"])
    if cycle:
        print("WARNING: depends_on has a cycle; card order falls back to input order.")
        return nodes
    return out


def _card_html(node: dict) -> tuple[str, str]:
    """Return (front, back) as HTML. Back appends a styled code-anchor chip."""
    front = node.get("card_front") or node.get("title", "")
    back = node.get("card_back") or node.get("summary", "")
    anchors = node.get("anchors") or []
    if anchors:
        chips = " ".join(f'<span class="anchor">{a}</span>' for a in anchors)
        # avoid duplicating an anchor already written into card_back prose
        if not any(a in back for a in anchors):
            back = f"{back}<br>{chips}"
    return front, back


def write_anki(nodes: list[dict], deck_name: str, out: Path) -> str:
    ordered = topo_order(nodes)
    try:
        import genanki  # type: ignore
    except ImportError:
        tsv = out.with_suffix(".tsv")
        lines = []
        for n in ordered:
            f, b = _card_html(n)
            f = f.replace("\t", " ").replace("\n", " ")
            b = b.replace("\t", " ").replace("\n", "<br>")
            lines.append(f"{f}\t{b}")
        tsv.write_text("\n".join(lines), encoding="utf-8")
        return (f"genanki not installed -> wrote {tsv.name} ({len(ordered)} cards). "
                f"Import in Anki: File > Import (field 1=Front, field 2=Back). "
                f"`pip install genanki` for a native .apkg.")

    model = genanki.Model(
        MODEL_ID, "repo-anki-mindmap Warm",
        fields=[{"name": "Front"}, {"name": "Back"}],
        css=ANKI_CSS,
        templates=[{
            "name": "Card 1",
            "qfmt": '<div class="q">{{Front}}</div>',
            "afmt": '<div class="q">{{Front}}</div><hr id="answer"><div class="a">{{Back}}</div>',
        }],
    )
    deck = genanki.Deck(DECK_ID, deck_name)
    for n in ordered:
        f, b = _card_html(n)
        deck.add_note(genanki.Note(model=model, fields=[f, b]))
    genanki.Package(deck).write_to_file(str(out))
    return f"wrote {out.name} ({len(ordered)} cards)."


def _outline(nodes: list[dict], title: str) -> str:
    """Nested Markdown from depends_on. Roots = nodes nothing depends on."""
    by_id = {n["id"]: n for n in nodes}
    children: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    has_parent: set[str] = set()
    for n in nodes:
        for dep in n.get("depends_on", []) or []:
            if dep in by_id:
                # dep is a prerequisite -> put the node UNDER its prerequisite
                children[dep].append(n["id"])
                has_parent.add(n["id"])
    roots = [n["id"] for n in nodes if n["id"] not in has_parent]
    lines = [f"# {title}", ""]
    seen: set[str] = set()

    def emit(nid: str, depth: int) -> None:
        if nid in seen:  # guard against cycles
            return
        seen.add(nid)
        node = by_id[nid]
        label = node.get("title", nid)
        grp = node.get("group")
        suffix = f"  _{grp}_" if grp and depth == 0 else ""
        lines.append(f"{'  ' * (depth + 1)}- {label}{suffix}")
        for c in children.get(nid, []):
            emit(c, depth + 1)

    for r in roots:
        emit(r, 0)
    return "\n".join(lines) + "\n"


# Self-contained mind-map page. markmap is loaded from the jsdelivr CDN at VIEW
# time (no npm install at build — corp TLS proxies choke on runtime `npx`), and
# the "Warm study / paper" world is baked into the page CSS. The markdown lives
# inline in a <script type="text/template"> the autoloader renders.
MAP_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — mind-map</title>
<style>
  :root {{ --paper:#faf6ef; --ink:#2b2622; }}
  @media (prefers-color-scheme: dark){{ :root{{ --paper:#211d1a; --ink:#efe7db; }} }}
  html, body {{ margin:0; height:100%; background:var(--paper);
    font-family:-apple-system,"Segoe UI","Inter",system-ui,sans-serif; }}
  svg.markmap {{ width:100vw; height:100vh; display:block; }}
  .markmap-node text {{ fill:var(--ink); font-weight:500; }}
  .markmap-link {{ stroke-opacity:.55; }}
</style>
</head><body>
<div class="markmap" style="width:100vw;height:100vh">
<script type="text/template">
{md}
</script>
</div>
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.18"></script>
</body></html>
"""


def _frontmatter() -> str:
    colors = ", ".join(f'"{c}"' for c in MAP_BRANCH_COLORS)
    return ("---\n"
            "markmap:\n"
            "  colorFreezeLevel: 2\n"
            "  initialExpandLevel: 3\n"
            "  maxWidth: 320\n"
            f"  color: [{colors}]\n"
            "---\n\n")


def write_mindmap(nodes: list[dict], title: str, out: Path) -> str:
    md = _frontmatter() + _outline(nodes, title)
    # .md alongside the HTML for offline use at https://markmap.js.org
    md_path = out.with_suffix(".md")  # out is "<base>.mindmap.html" -> "<base>.mindmap.md"
    md_path.write_text(md, encoding="utf-8")
    out.write_text(MAP_HTML.format(title=title, md=md), encoding="utf-8")
    return (f"wrote {out.name} (interactive mind-map, paper theme; loads markmap from the "
            f"CDN on first open — needs network then). Portable source: {md_path.name} "
            f"(render at https://markmap.js.org or with a local markmap-cli).")


def main() -> None:
    ap = argparse.ArgumentParser(description="concept-graph JSON -> Anki .apkg + Markmap .html")
    ap.add_argument("graph", type=Path, help="path to the concept-graph JSON")
    ap.add_argument("--deck-name", default="Repo study deck")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    ap.add_argument("--name", default=None, help="basename for outputs (default: from deck-name)")
    args = ap.parse_args()

    nodes = load_graph(args.graph)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = args.name or "".join(c if c.isalnum() else "-" for c in args.deck_name).strip("-").lower()

    anki_msg = write_anki(nodes, args.deck_name, args.out_dir / f"{base}.apkg")
    map_msg = write_mindmap(nodes, args.deck_name, args.out_dir / f"{base}.mindmap.html")
    print("Anki:   " + anki_msg)
    print("Mind-map: " + map_msg)


if __name__ == "__main__":
    main()
