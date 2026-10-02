#!/usr/bin/env python3
"""Render a concept-graph JSON into an interactive Markmap mind-map (.html) plus its .md source.

Input graph: a JSON list of nodes, each with at least {id, title}; see SCHEMA.md. The Anki deck
of the same graph is the `anki-deck` skill's job.

When the `easy-read` skill sits next to this one, its reading-comfort panel (fonts, spacing,
colour schemes, colour vision, focus highlight) is inlined into the page.

Degrades instead of failing: no network at view time -> the .md next to the map renders at
https://markmap.js.org. KISS: stdlib only, no network at build time.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concept_graph import load_graph, validate_nodes  # noqa: E402,F401  (re-exported for callers)

# Branch palette built on Okabe & Ito's colour-blind-safe set. Vermillion, blue and bluish green
# are the original hues; reddish purple, orange and sky blue are darkened just enough that every
# colour clears 3:1 against both paper backgrounds (#faf6ef light, #211d1a dark). Ordered so that
# neighbouring branches differ in lightness, not only in hue.
MAP_BRANCH_COLORS = ["#0072B2", "#D55E00", "#009E73", "#B5658F", "#B47A00", "#3A8FC4"]
MAP_ROOT_COLOR = "#8a7f73"

# Mind-map page template ("Warm study / paper"). markmap (d3 + markmap-lib + markmap-view) loads
# from the jsdelivr CDN at VIEW time: no npm at build (restricted networks often block runtime
# `npx`), and holding the Markmap instance enables the toolbar.
MAP_TEMPLATE = Path(__file__).resolve().parent / "map_template.html"
# Optional sibling skill: when installed next to this one, its reading-comfort panel is inlined.
EASY_READ_JS = Path(__file__).resolve().parent.parent / "easy-read" / "easy-read.js"


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
    meta = f"{len(nodes)} concepts" + (f" · {source}" if source else "")

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
    ap = argparse.ArgumentParser(description="concept-graph JSON -> Markmap .html + .md")
    ap.add_argument("graph", type=Path, help="path to the concept-graph JSON")
    ap.add_argument("--title", default="Mind-map")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    ap.add_argument("--name", default=None, help="basename for outputs (default: from title)")
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
    base = args.name or re.sub(r"[^\w]+", "-", args.title).strip("-").lower()
    print("Mind-map: " + write_mindmap(nodes, args.title, args.out_dir / f"{base}.mindmap.html", args.source))


if __name__ == "__main__":
    main()
