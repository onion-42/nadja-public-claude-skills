#!/usr/bin/env python3
"""Render a concept-graph JSON into an Anki deck (.apkg) and a Markmap mind-map (.html).

Input graph: a JSON list of nodes, each with at least {id, title, card_front,
card_back} and optionally {group, depends_on, anchors, summary, evidence}. See SKILL.md.
The graph can come from anywhere (a code repo, papers, session notes): this script
only renders it.

Degrades instead of failing:
- no genanki installed -> writes a TSV Anki can import (File > Import).
- no network at view time -> the .md next to the map renders at https://markmap.js.org.

KISS: stdlib + optional genanki. No network at build time, no config.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

# The note type keeps one stable id: every deck shares it, so cards keep their styling
# and re-imports update the model instead of cloning it.
MODEL_ID = 1091735104
MODEL_NAME = "anki-mindmap Warm"
EVIDENCE = ("shown", "plausible", "guess", "unverified")

# --- Shared "Warm study / paper" design system (site + Anki + mind-map) ---
# Muted branch palette; every colour clears 3:1 against both paper backgrounds
# (#faf6ef light, #211d1a dark), so links and swatches read in either theme.
MAP_BRANCH_COLORS = ["#b8683f", "#4f8a76", "#b07f22", "#6a82b0", "#a8628a", "#7c8f3e"]
MAP_ROOT_COLOR = "#8a7f73"

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
.a code, .source, .evidence {
  font-family: "SF Mono", "JetBrains Mono", ui-monospace, Menlo, monospace;
  font-size: .82em; background: var(--code-bg); color: var(--accent);
  padding: 2px 7px; border-radius: 6px; border: 1px solid var(--border);
  white-space: nowrap; }
.source, .evidence { display: inline-block; margin-top: 14px; }
.evidence { color: var(--ink-soft); }
.evidence.ev-shown { color: #4f8a76; }
.evidence.ev-guess, .evidence.ev-unverified { font-style: italic; }
.night_mode .card, .card.nightMode {
  --paper: #211d1a; --surface: #2a2521; --ink: #efe7db; --ink-soft: #b6ab9c;
  --accent: #e08a63; --code-bg: #2f2823; --border: #3d352d; }
"""


def deck_id_for(deck_name: str) -> int:
    """Stable per-deck id: decks with different names never merge in Anki."""
    return int(hashlib.sha1(deck_name.encode("utf-8")).hexdigest()[:8], 16) % (2**31 - 1) + 1


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def validate_nodes(data: object) -> list[dict]:
    """Check the whole graph shape; raise ValueError (callers decide whether to exit)."""
    if not isinstance(data, list):
        raise ValueError("graph JSON must be a list of nodes (or {'nodes': [...]}).")
    seen: set[str] = set()
    for i, n in enumerate(data):
        if not isinstance(n, dict) or "id" not in n or "title" not in n:
            raise ValueError(f"node {i} missing required 'id'/'title'.")
        if not isinstance(n["id"], str) or not n["id"].strip():
            raise ValueError(f"node {i} id must be a non-empty string, got {n['id']!r}.")
        if not isinstance(n["title"], str) or not n["title"].strip():
            raise ValueError(f"node {n['id']!r} title must be a non-empty string.")
        for key in ("depends_on", "anchors"):
            if not _is_str_list(n.get(key) or []):
                raise ValueError(f"node {n['id']!r} {key} must be a list of strings.")
        for key in ("group", "summary", "card_front", "card_back"):
            if n.get(key) is not None and not isinstance(n[key], str):
                raise ValueError(f"node {n['id']!r} {key} must be a string.")
        if n["id"] in seen:
            raise ValueError(f"duplicate node id {n['id']!r} (ids must be unique per graph).")
        seen.add(n["id"])
        ev = n.get("evidence")
        if ev is not None and ev not in EVIDENCE:
            raise ValueError(f"node {n['id']!r} has evidence {ev!r}; use one of {EVIDENCE}.")
    return data


def load_graph(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "nodes" in data:
        data = data["nodes"]
    return validate_nodes(data)


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
    """Return (front, back) as HTML. Back appends source-anchor and evidence chips."""
    front = node.get("card_front") or node.get("title", "")
    back = node.get("card_back") or node.get("summary", "")
    anchors = node.get("anchors") or []
    chips = []
    # skip an anchor already written into card_back prose
    chips += [f'<span class="source">{html.escape(a)}</span>' for a in anchors if a not in back]
    ev = node.get("evidence")
    if ev:
        chips.append(f'<span class="evidence ev-{ev}">{ev}</span>')
    if chips:
        back = f"{back}<br>{' '.join(chips)}"
    return front, back


def build_deck(nodes: list[dict], deck_name: str):
    """genanki Deck with a per-name deck id and per-card guids (raises ImportError without genanki)."""
    import genanki  # type: ignore

    model = genanki.Model(
        MODEL_ID, MODEL_NAME,
        fields=[{"name": "Front"}, {"name": "Back"}],
        css=ANKI_CSS,
        templates=[{
            "name": "Card 1",
            "qfmt": '<div class="q">{{Front}}</div>',
            "afmt": '<div class="q">{{Front}}</div><hr id="answer"><div class="a">{{Back}}</div>',
        }],
    )
    deck = genanki.Deck(deck_id_for(deck_name), deck_name)
    for n in topo_order(nodes):
        f, b = _card_html(n)
        # guid from (deck, node id), not from the text: an edited card updates in place
        deck.add_note(genanki.Note(model=model, fields=[f, b],
                                   guid=genanki.guid_for(deck_name, n["id"])))
    return deck


def write_anki(nodes: list[dict], deck_name: str, out: Path) -> str:
    try:
        deck = build_deck(nodes, deck_name)
    except ImportError:
        tsv = out.with_suffix(".tsv")
        lines = []
        for n in topo_order(nodes):
            f, b = _card_html(n)
            f = f.replace("\t", " ").replace("\n", " ")
            b = b.replace("\t", " ").replace("\n", "<br>")
            lines.append(f"{f}\t{b}")
        tsv.write_text("\n".join(lines), encoding="utf-8")
        return (f"genanki not installed -> wrote {tsv.name} ({len(lines)} cards). "
                f"Import in Anki: File > Import (field 1=Front, field 2=Back). "
                f"`pip install genanki` for a native .apkg.")
    import genanki  # type: ignore

    genanki.Package(deck).write_to_file(str(out))
    return f"wrote {out.name} ({len(deck.notes)} cards)."


def _md_escape(text: str) -> str:
    """Backslash-escape Markdown/HTML syntax so a title renders as literal text (no raw HTML)."""
    text = re.sub(r"([\\`*_\[\]<>#&!|~])", r"\\\1", " ".join(str(text).split()))
    # a leading "1." / "2)" / "-" / "+" would start a nested list and shift the tree order
    return re.sub(r"^(\d+)([.)])|^([-+])", lambda m: f"{m[1]}\\{m[2]}" if m[1] else f"\\{m[3]}", text)


def _label(node: dict) -> str:
    """Map label: escaped title plus an inline evidence chip when the node has one."""
    ev = node.get("evidence")
    title = _md_escape(node.get("title", node["id"]))
    return f"{title} `{ev}`" if ev else title


def _outline(nodes: list[dict], title: str) -> tuple[str, list]:
    """Nested Markdown from depends_on, plus the node ids in emit (depth-first) order.

    Roots = nodes nothing depends on. The id order matches markmap's tree walk
    (the root heading first -> None), so the page maps tree nodes to ids by position.
    """
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
    lines = [f"# {_md_escape(title)}", ""]
    order: list = [None]
    seen: set[str] = set()

    def emit(nid: str, depth: int) -> None:
        if nid in seen:  # guard against cycles
            return
        seen.add(nid)
        order.append(nid)
        lines.append(f"{'  ' * (depth + 1)}- {_label(by_id[nid])}")
        for c in children.get(nid, []):
            emit(c, depth + 1)

    for r in roots:
        emit(r, 0)
    if len(seen) < len(nodes):  # a cycle hides its nodes from every root: show them anyway
        print("WARNING: depends_on has a cycle; those nodes are shown as extra roots.")
        for n in nodes:
            emit(n["id"], 0)
    return "\n".join(lines) + "\n", order


def _group_colors(nodes: list[dict]) -> dict[str, str]:
    """group -> branch colour, in first-appearance order (drives map + legend)."""
    groups = list(dict.fromkeys(n.get("group") or "Other" for n in nodes))
    return {g: MAP_BRANCH_COLORS[i % len(MAP_BRANCH_COLORS)] for i, g in enumerate(groups)}


# Mind-map page template (same "Warm study / paper" world). markmap (d3 + markmap-lib +
# markmap-view) loads from the jsdelivr CDN at VIEW time: no npm at build (corp TLS
# proxies choke on runtime `npx`), and holding the Markmap instance enables the toolbar.
MAP_TEMPLATE = Path(__file__).resolve().parent / "map_template.html"
# Optional sibling skill: when installed next to this one, its reading-comfort panel is inlined.
EASY_READ_JS = Path(__file__).resolve().parent.parent / "easy-read" / "easy-read.js"


def _frontmatter() -> str:
    colors = ", ".join(f'"{c}"' for c in MAP_BRANCH_COLORS)
    return ("---\n"
            "markmap:\n"
            "  colorFreezeLevel: 2\n"
            "  initialExpandLevel: 3\n"
            "  maxWidth: 320\n"
            f"  color: [{colors}]\n"
            "---\n\n")


def write_mindmap(nodes: list[dict], title: str, out: Path, source: str = "") -> str:
    outline, order = _outline(nodes, title)
    md = _frontmatter() + outline
    # .md alongside the HTML for offline use at https://markmap.js.org
    md_path = out.with_suffix(".md")  # out is "<base>.mindmap.html" -> "<base>.mindmap.md"
    md_path.write_text(md, encoding="utf-8")
    colors = _group_colors(nodes)
    info = {n["id"]: {
        "title": n.get("title", n["id"]), "group": n.get("group") or "Other",
        "color": colors[n.get("group") or "Other"],
        "summary": n.get("summary") or n.get("card_back", ""),
        "anchors": n.get("anchors") or [], "evidence": n.get("evidence")} for n in nodes}
    legend = "".join(f'<li><span class="mm-swatch" style="background:{c}"></span>{html.escape(g)}</li>'
                     for g, c in colors.items())
    meta = f"{len(nodes)} cards" + (f" · {source}" if source else "")

    def js(obj: object) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    subs = {"__TITLE__": html.escape(title), "__META__": html.escape(meta), "__LEGEND__": legend,
            "__MD_JSON__": js(md), "__INFO_JSON__": js(info), "__ORDER_JSON__": js(order),
            "__ROOT_COLOR__": MAP_ROOT_COLOR,
            "__EASY_READ_JS__": (EASY_READ_JS.read_text(encoding="utf-8").replace("</", "<\\/")
                                 if EASY_READ_JS.exists() else "")}
    # one pass: a value that contains a placeholder name is never substituted again
    page = re.sub("|".join(subs), lambda m: subs[m.group(0)],
                  MAP_TEMPLATE.read_text(encoding="utf-8"))
    out.write_text(page, encoding="utf-8")
    return (f"wrote {out.name} (interactive mind-map, paper theme; loads markmap from the "
            f"CDN on first open — needs network then). Portable source: {md_path.name} "
            f"(render at https://markmap.js.org or with a local markmap-cli).")


def main() -> None:
    ap = argparse.ArgumentParser(description="concept-graph JSON -> Anki .apkg + Markmap .html")
    ap.add_argument("graph", type=Path, help="path to the concept-graph JSON")
    ap.add_argument("--deck-name", default="Study deck")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    ap.add_argument("--name", default=None, help="basename for outputs (default: from deck-name)")
    ap.add_argument("--source", default="",
                    help="shown in the map header, e.g. 'repo@abc123' or 'topic, 2026-09-23'")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        nodes = load_graph(args.graph)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = args.name or re.sub(r"[^\w]+", "-", args.deck_name).strip("-").lower()

    anki_msg = write_anki(nodes, args.deck_name, args.out_dir / f"{base}.apkg")
    map_msg = write_mindmap(nodes, args.deck_name, args.out_dir / f"{base}.mindmap.html", args.source)
    print("Anki:   " + anki_msg)
    print("Mind-map: " + map_msg)


if __name__ == "__main__":
    main()
