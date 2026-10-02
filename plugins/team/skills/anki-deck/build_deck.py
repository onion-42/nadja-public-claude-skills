#!/usr/bin/env python3
"""Render a concept-graph JSON into an Anki flashcard deck (.apkg).

Input graph: a JSON list of nodes, each with at least {id, title}; see SCHEMA.md. The graph can
come from anywhere (a code repo, papers, session notes): this script only renders it. The
mind-map of the same graph is the `mindmap` skill's job.

Reading comfort follows the `easy-read` skill's settings, baked into the note type at build
time (a live panel per card is unreliable inside Anki): --style nd (font + spacing + calm
colours), --font-file, --bionic, --cvd (colour vision).

Degrades instead of failing: no genanki installed -> writes a TSV Anki can import.
KISS: stdlib + optional genanki. No network, no config.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concept_graph import load_graph, validate_nodes  # noqa: E402,F401  (re-exported for callers)

# Note types keep stable ids: every deck shares one per look, so cards keep their styling and
# re-imports update the note type instead of cloning it. Each style / colour-vision variant gets
# its own id because its CSS and template differ.
MODEL_ID = 1091735104
MODEL_NAME = "anki-deck Warm"
MODEL_ID_ND = 1091735105
MODEL_NAME_ND = "anki-deck ND"
CVD_MODEL_OFFSET = {"off": 0, "red-green": 10, "blue-yellow": 20}
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
# OpenDyslexic (SIL OFL 1.1, fonts/OFL.txt) is Latin-only: Cyrillic falls through to the
# next font in the stack, e.g. one passed with --font-file.
OPENDYSLEXIC = {400: FONTS_DIR / "OpenDyslexic-400.woff2", 700: FONTS_DIR / "OpenDyslexic-700.woff2"}
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})

# Colour-vision daltonisation, same matrices as easy-read.js (tests/test_parity.py): Machado et al.
# 2009 dichromacy simulation (severity 1) + Fidaner et al. 2005 error shift, I + E(I - S), in linear
# RGB. They move the contrast a red-green or blue-yellow reader cannot see into channels they can.
CVD_MATRICES = {
    "red-green": "1 0 0 0 0 0.163 0.725 0.112 0 0 0.455 -0.645 1.191 0 0 0 0 0 1 0",
    "blue-yellow": "0.741 -0.407 0.666 0 0 0.075 0.585 0.34 0 0 0 0 1 0 0 0 0 0 1 0",
}

# Card face CSS ("Warm study / paper"). Phone-first, warm cream, high contrast, dark-mode aware
# (Anki adds .night_mode / .card.nightMode). Baked into the note type so a .apkg ships its own
# styling with no per-user setup.
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
.answer { font-weight: 700; margin: 0 0 10px; }
.points { margin: 0; padding-left: 1.1em; }
.points li { margin: 4px 0; }
.a img { display: block; max-width: 100%; height: auto; margin: 14px 0 0;
  border-radius: 8px; background: #fff; }
.night_mode .card, .card.nightMode {
  --paper: #211d1a; --surface: #2a2521; --ink: #efe7db; --ink-soft: #b6ab9c;
  --accent: #e08a63; --code-bg: #2f2823; --border: #3d352d; }
"""

# nd style: one sans font stack everywhere (no serif question), no italics, wider line,
# letter and word spacing, shorter measure, calm low-glare colours.
ND_CSS = """
.card, .q {
  font-family: __STACK__;
  letter-spacing: .03em; word-spacing: .14em; }
.card { line-height: 1.8; max-width: 36rem; --paper: #f7f1e3; --ink: #2d2a26; }
.q { font-size: 1.3em; line-height: 1.4; }
.a code, .source, .evidence { font-style: normal !important; white-space: normal; }
.points b { font-weight: 700; }
.night_mode .card, .card.nightMode { --paper: #262320; --ink: #e8e0d2; }
"""

# On html, not .card (= <body> in Anki): only the root element's filter leaves position:fixed
# elements (Anki's flag/mark icons) anchored to the window, and the page background is filtered too.
CVD_CSS = "\nhtml { filter: url(#er-cvd); }\n"
QFMT = '<div class="q">{{Front}}</div>'
AFMT = '<div class="q">{{Front}}</div><hr id="answer"><div class="a">{{Back}}</div>'


def anki_css(style: str, extra_fonts: list[str]) -> str:
    """Card CSS for a style. extra_fonts = media file names, stacked after OpenDyslexic."""
    if style == "warm":
        return ANKI_CSS
    faces = [f'@font-face {{ font-family: "ND OpenDyslexic"; font-weight: {w}; '
             f'src: url("_nd_opendyslexic-{w}.woff2") format("woff2"); }}' for w in OPENDYSLEXIC]
    faces += [f'@font-face {{ font-family: "ND Font {i}"; src: url("{name}"); }}'
              for i, name in enumerate(extra_fonts, 1)]
    stack = ", ".join(['"ND OpenDyslexic"', *(f'"ND Font {i}"' for i in range(1, len(extra_fonts) + 1)),
                       '"Segoe UI"', "system-ui", "sans-serif"])
    base = ANKI_CSS.replace(".evidence.ev-guess, .evidence.ev-unverified { font-style: italic; }\n", "")
    return "\n".join(faces) + base + ND_CSS.replace("__STACK__", stack)


def cvd_defs(cvd: str) -> str:
    """Inline SVG filter for a colour-vision mode ('' when off)."""
    if cvd == "off":
        return ""
    return ('<svg class="er-defs" width="0" height="0" style="position:absolute" aria-hidden="true" '
            'focusable="false"><filter id="er-cvd" color-interpolation-filters="linearRGB">'
            f'<feColorMatrix type="matrix" values="{CVD_MATRICES[cvd]}"/></filter></svg>')


def note_type_parts(style: str, extra_fonts: list[str], cvd: str = "off") -> tuple[str, str, str]:
    """(css, question template, answer template) for a style + colour-vision mode."""
    if cvd not in CVD_MODEL_OFFSET:
        raise ValueError(f"unknown colour-vision mode {cvd!r}; use one of {tuple(CVD_MODEL_OFFSET)}.")
    css = anki_css(style, extra_fonts) + (CVD_CSS if cvd != "off" else "")
    defs = cvd_defs(cvd)
    return css, defs + QFMT, defs + AFMT


def bionic(text: str) -> str:
    """Escaped HTML with the first half of each word bold (rounded up). Digits untouched."""
    def bold(w: str) -> str:
        k = (len(w) + 1) // 2
        return f"<b>{html.escape(w[:k])}</b>{html.escape(w[k:])}"
    parts = re.split(r"([^\W\d_]+)", text)  # odd indexes = words (letters only)
    return "".join(bold(p) if i % 2 else html.escape(p) for i, p in enumerate(parts))


def deck_id_for(deck_name: str) -> int:
    """Stable per-deck id: decks with different names never merge in Anki."""
    return int(hashlib.sha1(deck_name.encode("utf-8")).hexdigest()[:8], 16) % (2**31 - 1) + 1


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


def _card_html(node: dict, bionic_points: bool = False) -> tuple[str, str]:
    """Return (front, back) as HTML. Back appends source-anchor and evidence chips.

    Term cards: front = card_front or the title; back = the bold `answer` line plus up to
    3 short `points` (escaped here). Otherwise back = card_back (trusted HTML).
    """
    front = node.get("card_front") or node.get("title", "")
    if node.get("answer"):
        fmt = bionic if bionic_points else html.escape
        items = "".join(f"<li>{fmt(pt)}</li>" for pt in node.get("points") or [])
        back = f'<div class="answer">{html.escape(node["answer"])}</div>'
        back += f'<ul class="points">{items}</ul>' if items else ""
    else:
        back = node.get("card_back") or node.get("summary", "")
    if node.get("image"):  # embedded by write_anki under its basename
        back += f'<img src="{html.escape(Path(node["image"]).name)}">'
    anchors = node.get("anchors") or []
    # skip an anchor already written into card_back prose
    chips = [f'<span class="source">{html.escape(a)}</span>' for a in anchors if a not in back]
    ev = node.get("evidence")
    if ev:
        chips.append(f'<span class="evidence ev-{ev}">{ev}</span>')  # the label, not only a colour
    if chips:
        back = f"{back}<br>{' '.join(chips)}"
    return front, back


def font_media(style: str, fonts: list[Path]) -> dict[str, Path]:
    """Media file name -> source file for a style. `_` prefix: Anki's media check keeps them."""
    if style == "warm":
        return {}
    media = {f"_nd_opendyslexic-{w}.woff2": path for w, path in OPENDYSLEXIC.items()}
    media.update({f"_nd_font{i}{Path(f).suffix.lower()}": Path(f) for i, f in enumerate(fonts, 1)})
    return media


def image_media(nodes: list[dict], media_dir: Path) -> dict[str, Path]:
    """Media file name -> source file for node images, resolved against media_dir.

    An image must stay inside media_dir and be an image type: graphs are often written by an
    agent from sources it does not control, and a stray '../' must never pack a private file
    into a deck that gets shared. Anki stores media by file name, so names must be unique.
    """
    root = Path(media_dir).resolve()
    media: dict[str, Path] = {}
    for n in nodes:
        if not n.get("image"):
            continue
        src = (root / n["image"]).resolve()
        if not src.is_relative_to(root):
            raise ValueError(f"node {n['id']!r} image {n['image']!r} is outside the graph folder.")
        if src.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"node {n['id']!r} image {n['image']!r} is not an image type "
                             f"({', '.join(sorted(IMAGE_SUFFIXES))}).")
        if media.get(src.name, src) != src:
            raise ValueError(f"two different images share the file name {src.name!r}; rename one.")
        media[src.name] = src
    return media


def build_deck(nodes: list[dict], deck_name: str, style: str = "warm",
               fonts: list[Path] = (), bionic: bool = False, cvd: str = "off"):
    """genanki Deck with a per-name deck id and per-card guids (raises ImportError without genanki)."""
    import genanki  # type: ignore

    extra = [name for name in font_media(style, list(fonts)) if name.startswith("_nd_font")]
    css, qfmt, afmt = note_type_parts(style, extra, cvd)
    model_id, model_name = (MODEL_ID, MODEL_NAME) if style == "warm" else (MODEL_ID_ND, MODEL_NAME_ND)
    if cvd != "off":
        model_id, model_name = model_id + CVD_MODEL_OFFSET[cvd], f"{model_name} + {cvd}"
    model = genanki.Model(model_id, model_name, fields=[{"name": "Front"}, {"name": "Back"}],
                          css=css, templates=[{"name": "Card 1", "qfmt": qfmt, "afmt": afmt}])
    deck = genanki.Deck(deck_id_for(deck_name), deck_name)
    for n in topo_order(nodes):
        f, b = _card_html(n, bionic)
        # guid from (deck, node id), not from the text: an edited card updates in place
        deck.add_note(genanki.Note(model=model, fields=[f, b],
                                   guid=genanki.guid_for(deck_name, n["id"])))
    return deck


def _write_tsv(nodes: list[dict], out: Path, bionic: bool, images: dict[str, Path]) -> str:
    """Plain-text fallback: card text only; styling (--style, --cvd) needs the .apkg."""
    tsv = out.with_suffix(".tsv")
    lines = []
    for n in topo_order(nodes):
        f, b = _card_html(n, bionic)
        lines.append(f"{f.replace(chr(9), ' ').replace(chr(10), ' ')}\t"
                     f"{b.replace(chr(9), ' ').replace(chr(10), '<br>')}")
    tsv.write_text("\n".join(lines), encoding="utf-8")
    note = (f" Copy these images into Anki's collection.media folder by hand: "
            f"{', '.join(str(p) for p in images.values())}." if images else "")
    return (f"genanki not installed -> wrote {tsv.name} ({len(lines)} cards, no styling). "
            f"Import in Anki: File > Import (field 1=Front, field 2=Back).{note} "
            f"`pip install genanki` for a native .apkg.")


def write_anki(nodes: list[dict], deck_name: str, out: Path, style: str = "warm",
               fonts: list[Path] = (), bionic: bool = False, media_dir: Path = Path("."),
               cvd: str = "off") -> str:
    media = font_media(style, list(fonts))
    missing = [str(p) for p in media.values() if not p.is_file()]
    if missing:
        raise ValueError(f"font file(s) not found: {missing}")
    images = image_media(nodes, media_dir)
    missing = [str(p) for p in images.values() if not p.is_file()]
    if missing:
        raise ValueError(f"image file(s) not found: {missing}")
    media = {**media, **images}
    try:
        deck = build_deck(nodes, deck_name, style, fonts, bionic, cvd)
    except ImportError:
        return _write_tsv(nodes, out, bionic, images)
    import shutil
    import tempfile

    import genanki  # type: ignore

    with tempfile.TemporaryDirectory() as tmp:  # genanki names media by basename
        files = [shutil.copyfile(src, Path(tmp) / name) for name, src in media.items()]
        genanki.Package(deck, media_files=[str(f) for f in files]).write_to_file(str(out))
    media_note = f", {len(media)} media file(s) embedded" if media else ""
    return f"wrote {out.name} ({len(deck.notes)} cards{media_note})."


def main() -> None:
    ap = argparse.ArgumentParser(description="concept-graph JSON -> Anki .apkg")
    ap.add_argument("graph", type=Path, help="path to the concept-graph JSON")
    ap.add_argument("--deck-name", default="Study deck")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    ap.add_argument("--name", default=None, help="basename for the output (default: from deck-name)")
    ap.add_argument("--style", choices=("warm", "nd"), default="warm",
                    help="nd = ADHD/dyslexia/autism-friendly cards: OpenDyslexic, spacing, no italics")
    ap.add_argument("--font-file", type=Path, action="append", default=[],
                    help="nd style: extra font embedded after OpenDyslexic (e.g. one with Cyrillic); repeatable")
    ap.add_argument("--bionic", action="store_true", help="bold the first half of each word in points")
    ap.add_argument("--cvd", choices=tuple(CVD_MODEL_OFFSET), default="off",
                    help="colour vision: daltonise card colours and images for red-green or blue-yellow readers")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        nodes = load_graph(args.graph)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        base = args.name or re.sub(r"[^\w]+", "-", args.deck_name).strip("-").lower()
        msg = write_anki(nodes, args.deck_name, args.out_dir / f"{base}.apkg", args.style,
                         args.font_file, args.bionic, media_dir=args.graph.parent, cvd=args.cvd)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    print("Anki: " + msg)


if __name__ == "__main__":
    main()
