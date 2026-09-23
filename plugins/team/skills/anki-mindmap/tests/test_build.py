"""Tests for the anki-mindmap core renderer (build.py)."""
from __future__ import annotations

import builtins
import importlib.util
import json
from pathlib import Path

import pytest

needs_genanki = pytest.mark.skipif(importlib.util.find_spec("genanki") is None,
                                   reason="genanki not installed")

SKILL_DIR = Path(__file__).resolve().parents[1]
EXAMPLE = SKILL_DIR / "examples" / "graph.example.json"


def _load_build():
    spec = importlib.util.spec_from_file_location("anki_build", SKILL_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = _load_build()


def _write(tmp_path: Path, nodes: list[dict]) -> Path:
    p = tmp_path / "g.json"
    p.write_text(json.dumps(nodes), encoding="utf-8")
    return p


NODES = [
    {"id": "cls", "title": "CLS token", "group": "Concepts", "kind": "concept",
     "card_front": "What is the CLS token?", "card_back": "A learned summary token.",
     "anchors": ["arXiv:1810.04805 §3"], "evidence": "shown"},
    {"id": "concat", "title": "CLS ‖ mean concat", "group": "Methods", "kind": "method",
     "depends_on": ["cls"], "card_front": "Why concat CLS and mean?",
     "card_back": "They carry complementary signal.", "evidence": "plausible"},
]


# --- ids -------------------------------------------------------------------------

def test_deck_id_differs_per_deck_name():
    assert build.deck_id_for("Deck A") != build.deck_id_for("Deck B")


def test_deck_id_is_stable_and_in_anki_range():
    a = build.deck_id_for("Claude: как и почему")
    assert a == build.deck_id_for("Claude: как и почему")
    assert 0 < a < 2**31


@needs_genanki
def test_note_guid_survives_editing_the_card_text():
    deck1 = build.build_deck(NODES, "Study")
    edited = [dict(NODES[0], card_back="Rewritten answer."), NODES[1]]
    deck2 = build.build_deck(edited, "Study")
    assert [n.guid for n in deck1.notes] == [n.guid for n in deck2.notes]


@needs_genanki
def test_note_guid_differs_across_decks_for_same_node_id():
    g1 = build.build_deck(NODES, "Deck A").notes[0].guid
    g2 = build.build_deck(NODES, "Deck B").notes[0].guid
    assert g1 != g2


@needs_genanki
def test_build_deck_uses_per_name_deck_id():
    assert build.build_deck(NODES, "Deck A").deck_id == build.deck_id_for("Deck A")


# --- validation --------------------------------------------------------------------

def test_load_graph_rejects_unknown_evidence(tmp_path):
    bad = [dict(NODES[0], evidence="vibes")]
    with pytest.raises(ValueError):
        build.load_graph(_write(tmp_path, bad))


def test_load_graph_rejects_duplicate_ids(tmp_path):
    with pytest.raises(ValueError):
        build.load_graph(_write(tmp_path, [NODES[0], NODES[0]]))


# --- cards -------------------------------------------------------------------------

def test_card_back_has_evidence_chip_and_anchor():
    _, back = build._card_html(NODES[0])
    assert 'class="evidence ev-shown"' in back
    assert 'class="source"' in back


def test_card_without_evidence_has_no_chip():
    _, back = build._card_html({"id": "x", "title": "X", "card_back": "b"})
    assert "evidence" not in back


# --- mind-map ----------------------------------------------------------------------

def test_mindmap_has_header_legend_toolbar_and_theme(tmp_path):
    out = tmp_path / "s.mindmap.html"
    build.write_mindmap(NODES, "Study", out, source="unit test, 2026-09-23")
    html = out.read_text(encoding="utf-8")
    for needle in ('class="mm-header"', 'class="mm-legend"', 'id="mm-fit"',
                   'id="mm-expand"', 'id="mm-collapse"', 'id="mm-theme"', 'id="mm-details"',
                   "data-theme", "unit test, 2026-09-23",
                   "2 cards", "prefers-color-scheme: dark"):
        assert needle in html, needle
    # one legend swatch per group
    assert html.count('class="mm-swatch"') == 2


def test_mindmap_details_payload_has_summary_anchors_evidence(tmp_path):
    out = tmp_path / "s.mindmap.html"
    build.write_mindmap(NODES, "Study", out)
    html = out.read_text(encoding="utf-8")
    assert "arXiv:1810.04805 §3" in html      # anchor reaches the details panel
    assert "A learned summary token." in html  # card_back as the fallback summary


def test_mindmap_labels_carry_evidence(tmp_path):
    out = tmp_path / "s.mindmap.html"
    build.write_mindmap(NODES, "Study", out)
    md = out.with_suffix(".md").read_text(encoding="utf-8")
    assert "CLS token `shown`" in md


# --- regression + fallback -----------------------------------------------------------

@needs_genanki
def test_example_graph_still_renders(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["build.py", str(EXAMPLE), "--deck-name", "Example",
                                     "--out-dir", str(tmp_path)])
    build.main()
    assert (tmp_path / "example.apkg").stat().st_size > 0
    assert (tmp_path / "example.mindmap.html").exists()


def test_tsv_fallback_without_genanki(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def no_genanki(name, *args, **kwargs):
        if name == "genanki":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_genanki)
    msg = build.write_anki(NODES, "Study", tmp_path / "s.apkg")
    assert "genanki not installed" in msg
    assert len((tmp_path / "s.tsv").read_text(encoding="utf-8").splitlines()) == 2


# --- code-review edge cases ------------------------------------------------------------

def _page(tmp_path, nodes, title="Study"):
    out = tmp_path / "s.mindmap.html"
    build.write_mindmap(nodes, title, out)
    return out.read_text(encoding="utf-8"), out.with_suffix(".md").read_text(encoding="utf-8")


def test_placeholder_in_title_does_not_leak_json(tmp_path):
    page, _ = _page(tmp_path, NODES, title="Deck __INFO_JSON__ x")
    h1 = page.split('<h1 class="mm-title">')[1].split("</h1>")[0]
    assert h1 == "Deck __INFO_JSON__ x"


def test_info_is_keyed_by_node_id_in_outline_order(tmp_path):
    nodes = [dict(NODES[0], title="a & b __init__"), dict(NODES[1], title="a & b __init__")]
    page, _ = _page(tmp_path, nodes)
    order = json.loads(page.split("const ORDER = ")[1].split(";")[0])
    info = json.loads(page.split("const INFO = ")[1].split(";  //")[0])
    assert order == [None, "cls", "concat"]  # root heading first, then DFS outline items
    assert set(info) == {"cls", "concat"}     # duplicate titles no longer collide


def test_title_html_is_escaped_in_map_labels(tmp_path):
    nodes = [dict(NODES[0], title='<img src=x onerror=alert(1)> __init__ *x*')]
    _, md = _page(tmp_path, nodes)
    assert r"\<img" in md and md.count("<") == md.count(r"\<")  # every < is escaped
    assert r"\_\_init\_\_" in md and r"\*x\*" in md


def test_cycle_nodes_still_appear_in_outline(tmp_path, capsys):
    nodes = [dict(NODES[0], depends_on=["concat"]), NODES[1]]
    page, md = _page(tmp_path, nodes)
    assert "CLS token" in md and "mean concat" in md
    order = json.loads(page.split("const ORDER = ")[1].split(";")[0])
    assert sorted(x for x in order if x) == ["cls", "concat"]
    assert "cycle" in capsys.readouterr().out


def test_anchor_html_is_escaped_on_card():
    _, back = build._card_html(dict(NODES[0], anchors=["a<b>c"]))
    assert "a&lt;b&gt;c" in back and "<b>" not in back


def test_anchor_already_in_back_is_filtered_per_anchor():
    node = dict(NODES[0], card_back="see x.py:3", anchors=["x.py:3", "y.py:9"])
    _, back = build._card_html(node)
    assert back.count("x.py:3") == 1 and 'class="source">y.py:9' in back


@pytest.mark.parametrize("bad", [{"id": 1, "title": "t"},
                                 {"id": "a", "title": "t", "depends_on": "b"}])
def test_load_graph_rejects_bad_types(tmp_path, bad):
    with pytest.raises(ValueError):
        build.load_graph(_write(tmp_path, [bad]))


# --- easy-read widget ------------------------------------------------------------------

def test_mindmap_inlines_easy_read_widget_when_available(tmp_path):
    page, _ = _page(tmp_path, NODES)
    assert "window.__easyRead" in page
    assert "__EASY_READ_JS__" not in page


def test_mindmap_renders_without_easy_read(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "EASY_READ_JS", tmp_path / "missing.js")
    page, _ = _page(tmp_path, NODES)
    assert "window.__easyRead" not in page and "__EASY_READ_JS__" not in page


# --- second review: raise (not exit), full shape, list-like titles ------------------------

@pytest.mark.parametrize("bad", [
    {"id": "a", "title": "t", "anchors": [{"url": "x"}]},
    {"id": "a", "title": "t", "group": ["x"]},
    {"id": "a", "title": "t", "depends_on": [1]},
    {"id": "a", "title": "   "},
])
def test_validate_nodes_raises_value_error_not_system_exit(bad):
    with pytest.raises(ValueError):
        build.validate_nodes([bad])


@pytest.mark.parametrize("title", ["1. Why hooks", "2) Why hooks", "- dash", "+ plus"])
def test_list_like_titles_are_escaped(tmp_path, title):
    _, md = _page(tmp_path, [dict(NODES[0], title=title)])
    label = md.splitlines()[-1].split("- ", 1)[1]
    assert label.startswith("\\") or "\." in label or "\)" in label, label


# --- term cards (answer + points), nd style, fonts, bionic -------------------------

TERM = {"id": "koleo", "title": "KoLeo regularizer", "group": "Methods",
        "answer": "Pushes embeddings apart from each other.",
        "points": ["Penalizes a close neighbour in the batch", "Helps retrieval most"],
        "anchors": ["arXiv:2304.07193 §4"], "evidence": "shown"}


def test_term_card_front_defaults_to_title():
    front, _ = build._card_html(TERM)
    assert front == "KoLeo regularizer"


def test_term_card_back_is_answer_line_then_points():
    _, back = build._card_html(TERM)
    assert '<div class="answer">Pushes embeddings apart from each other.</div>' in back
    assert back.count("<li>") == 2
    assert back.index('class="answer"') < back.index('<ul class="points">') < back.index('class="source"')


def test_term_card_text_is_html_escaped():
    _, back = build._card_html(dict(TERM, answer="a <b> & c", points=["<script>x</script>"]))
    assert "&lt;b&gt; &amp; c" in back and "<script>" not in back


def test_load_graph_rejects_more_than_three_points(tmp_path):
    with pytest.raises(ValueError):
        build.load_graph(_write(tmp_path, [dict(TERM, points=["a", "b", "c", "d"])]))


@pytest.mark.parametrize("bad", [{"answer": 3}, {"points": "one string"}, {"points": [1]}])
def test_load_graph_rejects_bad_term_fields(tmp_path, bad):
    with pytest.raises(ValueError):
        build.load_graph(_write(tmp_path, [dict(TERM, **bad)]))


def test_bionic_bolds_word_starts_in_points_only():
    _, back = build._card_html(TERM, bionic_points=True)
    assert "<b>Penal</b>izes" in back           # points: word starts bold
    assert "<b>Push" not in back                 # the answer line is bold as a whole via CSS
    assert "<b>" not in build._card_html(TERM)[1]


def test_bionic_keeps_cyrillic_and_numbers():
    assert build.bionic("штраф 55.6") == "<b>штр</b>аф 55.6"


def test_nd_css_stacks_opendyslexic_then_extra_fonts():
    css = build.anki_css("nd", ["_nd_font1.ttf"])
    assert css.index('"ND OpenDyslexic"') < css.index('"ND Font 1"')
    assert 'url("_nd_font1.ttf")' in css
    assert "font-style: italic" not in css


def test_warm_css_is_unchanged_default():
    assert build.anki_css("warm", []) == build.ANKI_CSS


@needs_genanki
def test_nd_deck_uses_its_own_note_type():
    warm = build.build_deck([TERM], "Study")
    nd = build.build_deck([TERM], "Study", style="nd")
    assert warm.notes[0].model.model_id != nd.notes[0].model.model_id
    assert warm.notes[0].guid == nd.notes[0].guid


@needs_genanki
def test_nd_apkg_embeds_opendyslexic_and_extra_font(tmp_path):
    import zipfile
    font = tmp_path / "MyFont.ttf"
    font.write_bytes(b"\x00\x01\x00\x00fake")
    out = tmp_path / "d.apkg"
    build.write_anki([TERM], "Study", out, style="nd", fonts=[font])
    media = json.loads(zipfile.ZipFile(out).read("media"))
    assert {"_nd_opendyslexic-400.woff2", "_nd_font1.ttf"} <= set(media.values())
