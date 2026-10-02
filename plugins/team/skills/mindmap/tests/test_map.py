"""Tests for the mindmap renderer (build_map.py)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
EXAMPLE = SKILL_DIR / "examples" / "graph.example.json"


def _load(name: str, file: str):
    sys.path.insert(0, str(SKILL_DIR))  # build_map imports its sibling concept_graph.py
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mm = _load("mindmap_build", "build_map.py")

NODES = [
    {"id": "cls", "title": "CLS token", "group": "Concepts", "kind": "concept",
     "card_front": "What is the CLS token?", "card_back": "A learned summary token.",
     "anchors": ["arXiv:1810.04805 §3"], "evidence": "shown"},
    {"id": "concat", "title": "CLS ‖ mean concat", "group": "Methods", "kind": "method",
     "depends_on": ["cls"], "card_front": "Why concat CLS and mean?",
     "card_back": "They carry complementary signal.", "evidence": "plausible"},
]


def _page(tmp_path, nodes, title="Study", source=""):
    out = tmp_path / "s.mindmap.html"
    mm.write_mindmap(nodes, title, out, source=source)
    return out.read_text(encoding="utf-8"), out.with_suffix(".md").read_text(encoding="utf-8")


# --- structure ---------------------------------------------------------------------

def test_mindmap_has_header_legend_toolbar_and_theme(tmp_path):
    page, _ = _page(tmp_path, NODES, source="unit test, 2026-09-23")
    for needle in ('class="mm-header"', 'class="mm-legend"', 'id="mm-fit"',
                   'id="mm-expand"', 'id="mm-collapse"', 'id="mm-theme"', 'id="mm-details"',
                   "data-theme", "unit test, 2026-09-23",
                   "2 concepts", "prefers-color-scheme: dark"):
        assert needle in page, needle
    assert page.count('class="mm-swatch"') == 2  # one legend swatch per group


def test_mindmap_details_payload_has_summary_anchors_evidence(tmp_path):
    page, _ = _page(tmp_path, NODES)
    assert "arXiv:1810.04805 §3" in page
    assert "A learned summary token." in page  # card_back as the fallback summary


def test_mindmap_labels_carry_evidence(tmp_path):
    _, md = _page(tmp_path, NODES)
    assert "CLS token `shown`" in md


def test_placeholder_in_title_does_not_leak_json(tmp_path):
    page, _ = _page(tmp_path, NODES, title="Deck __INFO_JSON__ x")
    h1 = page.split('<h1 class="mm-title">')[1].split("</h1>")[0]
    assert h1 == "Deck __INFO_JSON__ x"


def test_info_is_keyed_by_node_id_in_outline_order(tmp_path):
    nodes = [dict(NODES[0], title="a & b __init__"), dict(NODES[1], title="a & b __init__")]
    page, _ = _page(tmp_path, nodes)
    order = json.loads(page.split("const ORDER = ")[1].split(";")[0])
    info = json.loads(page.split("const INFO = ")[1].split(";  //")[0])
    assert order == [None, "cls", "concat"]
    assert set(info) == {"cls", "concat"}


def test_title_html_is_escaped_in_map_labels(tmp_path):
    _, md = _page(tmp_path, [dict(NODES[0], title='<img src=x onerror=alert(1)> __init__ *x*')])
    assert r"\<img" in md and md.count("<") == md.count(r"\<")
    assert r"\_\_init\_\_" in md and r"\*x\*" in md


def test_cycle_nodes_still_appear_in_outline(tmp_path, capsys):
    page, md = _page(tmp_path, [dict(NODES[0], depends_on=["concat"]), NODES[1]])
    assert "CLS token" in md and "mean concat" in md
    order = json.loads(page.split("const ORDER = ")[1].split(";")[0])
    assert sorted(x for x in order if x) == ["cls", "concat"]
    assert "cycle" in capsys.readouterr().out


@pytest.mark.parametrize("title", ["1. Why hooks", "2) Why hooks", "- dash", "+ plus"])
def test_list_like_titles_are_escaped(tmp_path, title):
    _, md = _page(tmp_path, [dict(NODES[0], title=title)])
    label = md.splitlines()[-1].split("- ", 1)[1]
    assert label.startswith("\\") or "\\." in label or "\\)" in label, label


def test_load_graph_rejects_duplicate_ids(tmp_path):
    p = tmp_path / "g.json"
    p.write_text(json.dumps([NODES[0], NODES[0]]), encoding="utf-8")
    with pytest.raises(ValueError):
        mm.load_graph(p)


# --- colour: Okabe-Ito branches, readable in both themes ----------------------------------

def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("paper", ["#faf6ef", "#211d1a"])
def test_branch_colours_clear_3_to_1_on_both_themes(paper):
    for colour in [*mm.MAP_BRANCH_COLORS, mm.MAP_ROOT_COLOR]:
        assert _contrast(colour, paper) >= 3.0, (colour, paper)


def test_branch_palette_is_okabe_ito_based():
    # vermillion, blue and bluish green are the unmodified Okabe-Ito hues
    assert {"#D55E00", "#0072B2", "#009E73"} <= set(mm.MAP_BRANCH_COLORS)
    assert len(set(mm.MAP_BRANCH_COLORS)) == len(mm.MAP_BRANCH_COLORS) == 6


# --- easy-read widget ------------------------------------------------------------------

def test_mindmap_inlines_easy_read_widget_when_available(tmp_path):
    page, _ = _page(tmp_path, NODES)
    assert "window.__easyRead" in page and "__EASY_READ_JS__" not in page


def test_mindmap_renders_without_easy_read(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "EASY_READ_JS", tmp_path / "missing.js")
    page, _ = _page(tmp_path, NODES)
    assert "window.__easyRead" not in page and "__EASY_READ_JS__" not in page


# --- CLI -----------------------------------------------------------------------------

def test_example_graph_renders_map_only(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["build_map.py", str(EXAMPLE), "--title", "Example",
                                     "--out-dir", str(tmp_path)])
    mm.main()
    assert (tmp_path / "example.mindmap.html").exists()
    assert (tmp_path / "example.mindmap.md").exists()
    assert not (tmp_path / "example.apkg").exists()  # the deck is the anki-deck skill's job
