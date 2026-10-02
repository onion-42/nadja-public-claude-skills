"""Tests for the anki-deck renderer (build_deck.py)."""
from __future__ import annotations

import builtins
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

needs_genanki = pytest.mark.skipif(importlib.util.find_spec("genanki") is None,
                                   reason="genanki not installed")

SKILL_DIR = Path(__file__).resolve().parents[1]
EXAMPLE = SKILL_DIR / "examples" / "graph.example.json"


def _load(name: str, file: str):
    sys.path.insert(0, str(SKILL_DIR))  # build_deck imports its sibling concept_graph.py
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


deck = _load("anki_deck_build", "build_deck.py")


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

TERM = {"id": "koleo", "title": "KoLeo regularizer", "group": "Methods",
        "answer": "Pushes embeddings apart from each other.",
        "points": ["Penalizes a close neighbour in the batch", "Helps retrieval most"],
        "anchors": ["arXiv:2304.07193 §4"], "evidence": "shown"}


# --- ids -------------------------------------------------------------------------

def test_deck_id_differs_per_deck_name():
    assert deck.deck_id_for("Deck A") != deck.deck_id_for("Deck B")


def test_deck_id_is_stable_and_in_anki_range():
    a = deck.deck_id_for("Claude: как и почему")
    assert a == deck.deck_id_for("Claude: как и почему")
    assert 0 < a < 2**31


@needs_genanki
def test_note_guid_survives_editing_the_card_text():
    deck1 = deck.build_deck(NODES, "Study")
    edited = [dict(NODES[0], card_back="Rewritten answer."), NODES[1]]
    deck2 = deck.build_deck(edited, "Study")
    assert [n.guid for n in deck1.notes] == [n.guid for n in deck2.notes]


@needs_genanki
def test_note_guid_differs_across_decks_for_same_node_id():
    g1 = deck.build_deck(NODES, "Deck A").notes[0].guid
    g2 = deck.build_deck(NODES, "Deck B").notes[0].guid
    assert g1 != g2


@needs_genanki
def test_build_deck_uses_per_name_deck_id():
    assert deck.build_deck(NODES, "Deck A").deck_id == deck.deck_id_for("Deck A")


# --- validation (shared concept_graph.py) ----------------------------------------------

def test_load_graph_rejects_unknown_evidence(tmp_path):
    with pytest.raises(ValueError):
        deck.load_graph(_write(tmp_path, [dict(NODES[0], evidence="vibes")]))


def test_load_graph_rejects_duplicate_ids(tmp_path):
    with pytest.raises(ValueError):
        deck.load_graph(_write(tmp_path, [NODES[0], NODES[0]]))


@pytest.mark.parametrize("bad", [{"id": 1, "title": "t"},
                                 {"id": "a", "title": "t", "depends_on": "b"},
                                 {"id": "a", "title": "t", "anchors": [{"url": "x"}]},
                                 {"id": "a", "title": "t", "group": ["x"]},
                                 {"id": "a", "title": "   "}])
def test_validate_nodes_raises_value_error(bad):
    with pytest.raises(ValueError):
        deck.validate_nodes([bad])


def test_load_graph_rejects_more_than_three_points(tmp_path):
    with pytest.raises(ValueError):
        deck.load_graph(_write(tmp_path, [dict(TERM, points=["a", "b", "c", "d"])]))


@pytest.mark.parametrize("bad", [{"answer": 3}, {"points": "one string"}, {"points": [1]},
                                 {"image": ["a.png"]}])
def test_load_graph_rejects_bad_term_fields(tmp_path, bad):
    with pytest.raises(ValueError):
        deck.load_graph(_write(tmp_path, [dict(TERM, **bad)]))


# --- order -------------------------------------------------------------------------

def test_topo_order_puts_prerequisites_first():
    assert [n["id"] for n in deck.topo_order(list(reversed(NODES)))] == ["cls", "concat"]


def test_topo_order_falls_back_on_cycle(capsys):
    nodes = [dict(NODES[0], depends_on=["concat"]), NODES[1]]
    assert deck.topo_order(nodes) == nodes
    assert "cycle" in capsys.readouterr().out


# --- cards -------------------------------------------------------------------------

def test_card_back_has_evidence_chip_and_anchor():
    _, back = deck._card_html(NODES[0])
    assert 'class="evidence ev-shown"' in back and 'class="source"' in back


def test_card_without_evidence_has_no_chip():
    _, back = deck._card_html({"id": "x", "title": "X", "card_back": "b"})
    assert "evidence" not in back


def test_anchor_html_is_escaped_on_card():
    _, back = deck._card_html(dict(NODES[0], anchors=["a<b>c"]))
    assert "a&lt;b&gt;c" in back and "<b>" not in back


def test_anchor_already_in_back_is_filtered_per_anchor():
    node = dict(NODES[0], card_back="see x.py:3", anchors=["x.py:3", "y.py:9"])
    _, back = deck._card_html(node)
    assert back.count("x.py:3") == 1 and 'class="source">y.py:9' in back


def test_term_card_front_defaults_to_title():
    assert deck._card_html(TERM)[0] == "KoLeo regularizer"


def test_term_card_back_is_answer_line_then_points():
    _, back = deck._card_html(TERM)
    assert '<div class="answer">Pushes embeddings apart from each other.</div>' in back
    assert back.count("<li>") == 2
    assert back.index('class="answer"') < back.index('<ul class="points">') < back.index('class="source"')


def test_term_card_text_is_html_escaped():
    _, back = deck._card_html(dict(TERM, answer="a <b> & c", points=["<script>x</script>"]))
    assert "&lt;b&gt; &amp; c" in back and "<script>" not in back


def test_bionic_bolds_word_starts_in_points_only():
    _, back = deck._card_html(TERM, bionic_points=True)
    assert "<b>Penal</b>izes" in back
    assert "<b>Push" not in back
    assert "<b>" not in deck._card_html(TERM)[1]


def test_bionic_keeps_cyrillic_and_numbers():
    assert deck.bionic("штраф 55.6") == "<b>штр</b>аф 55.6"


# --- nd style + fonts ------------------------------------------------------------------

def test_nd_css_stacks_opendyslexic_then_extra_fonts():
    css = deck.anki_css("nd", ["_nd_font1.ttf"])
    assert css.index('"ND OpenDyslexic"') < css.index('"ND Font 1"')
    assert 'url("_nd_font1.ttf")' in css
    assert "font-style: italic" not in css


def test_warm_css_is_unchanged_default():
    assert deck.anki_css("warm", []) == deck.ANKI_CSS


@needs_genanki
def test_nd_deck_uses_its_own_note_type():
    warm = deck.build_deck([TERM], "Study")
    nd = deck.build_deck([TERM], "Study", style="nd")
    assert warm.notes[0].model.model_id != nd.notes[0].model.model_id
    assert warm.notes[0].guid == nd.notes[0].guid


@needs_genanki
def test_nd_apkg_embeds_opendyslexic_and_extra_font(tmp_path):
    font = tmp_path / "MyFont.ttf"
    font.write_bytes(b"\x00\x01\x00\x00fake")
    out = tmp_path / "d.apkg"
    deck.write_anki([TERM], "Study", out, style="nd", fonts=[font])
    media = json.loads(zipfile.ZipFile(out).read("media"))
    assert {"_nd_opendyslexic-400.woff2", "_nd_font1.ttf"} <= set(media.values())


# --- colour vision (easy-read's "Colour vision" setting, baked into the note type) -----

@pytest.mark.parametrize("cvd", ["red-green", "blue-yellow"])
def test_cvd_template_carries_filter_and_css_applies_it(cvd):
    css, qfmt, afmt = deck.note_type_parts("warm", [], cvd)
    matrix = deck.CVD_MATRICES[cvd]
    for fmt in (qfmt, afmt):
        assert '<filter id="er-cvd"' in fmt and f'values="{matrix}"' in fmt
    # on html, not .card (= <body> in Anki): only the root element keeps fixed elements in place
    assert "html { filter: url(#er-cvd); }" in css


def test_cvd_off_adds_nothing():
    css, qfmt, _ = deck.note_type_parts("warm", [], "off")
    assert "er-cvd" not in css and "er-cvd" not in qfmt


def test_cvd_matrices_are_4x5():
    for values in deck.CVD_MATRICES.values():
        assert len(values.split()) == 20


@needs_genanki
def test_cvd_deck_uses_its_own_note_type_and_keeps_guids():
    plain = deck.build_deck([TERM], "Study")
    rg = deck.build_deck([TERM], "Study", cvd="red-green")
    by = deck.build_deck([TERM], "Study", cvd="blue-yellow")
    ids = {plain.notes[0].model.model_id, rg.notes[0].model.model_id, by.notes[0].model.model_id}
    assert len(ids) == 3
    assert plain.notes[0].guid == rg.notes[0].guid == by.notes[0].guid


# --- images ----------------------------------------------------------------------

def test_card_back_shows_image_after_points_before_chips():
    _, back = deck._card_html(dict(TERM, image="img/koleo plot.png"))
    assert '<img src="koleo plot.png">' in back
    assert back.index('<ul class="points">') < back.index("<img") < back.index('class="source"')


@needs_genanki
def test_apkg_embeds_node_image_relative_to_media_dir(tmp_path):
    (tmp_path / "img").mkdir()
    (tmp_path / "img" / "pic.png").write_bytes(b"\x89PNGfake")
    out = tmp_path / "d.apkg"
    deck.write_anki([dict(TERM, image="img/pic.png")], "Study", out, media_dir=tmp_path)
    assert "pic.png" in json.loads(zipfile.ZipFile(out).read("media")).values()


@pytest.mark.parametrize("path", ["../secret.png", "img/../../secret.png"])
def test_image_outside_graph_dir_is_rejected(tmp_path, path):
    (tmp_path / "graph").mkdir()
    (tmp_path / "secret.png").write_bytes(b"\x89PNGfake")
    with pytest.raises(ValueError, match="outside"):
        deck.image_media([dict(TERM, image=path)], tmp_path / "graph")


def test_absolute_image_path_is_rejected(tmp_path):
    pic = tmp_path / "pic.png"
    pic.write_bytes(b"\x89PNGfake")
    with pytest.raises(ValueError, match="outside"):
        deck.image_media([dict(TERM, image=str(pic))], tmp_path / "graph")


def test_non_image_file_is_rejected(tmp_path):
    (tmp_path / "credentials").write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError, match="image type"):
        deck.image_media([dict(TERM, image="credentials")], tmp_path)


def test_two_images_with_the_same_basename_are_rejected(tmp_path):
    nodes = [dict(TERM, image="a/fig.png"), dict(TERM, id="other", image="b/fig.png")]
    with pytest.raises(ValueError, match="fig.png"):
        deck.image_media(nodes, tmp_path)


def test_tsv_fallback_lists_images_to_copy(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def no_genanki(name, *args, **kwargs):
        if name == "genanki":
            raise ImportError
        return real_import(name, *args, **kwargs)

    (tmp_path / "pic.png").write_bytes(b"\x89PNGfake")
    monkeypatch.setattr(builtins, "__import__", no_genanki)
    msg = deck.write_anki([dict(TERM, image="pic.png")], "Study", tmp_path / "s.apkg", media_dir=tmp_path)
    assert "collection.media" in msg and "pic.png" in msg


def test_missing_image_file_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="image"):
        deck.write_anki([dict(TERM, image="nope.png")], "Study", tmp_path / "d.apkg",
                        media_dir=tmp_path)


# --- regression + fallback -----------------------------------------------------------

@needs_genanki
def test_example_graph_still_renders(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["build_deck.py", str(EXAMPLE), "--deck-name", "Example",
                                     "--out-dir", str(tmp_path), "--cvd", "red-green"])
    deck.main()
    assert (tmp_path / "example.apkg").stat().st_size > 0
    assert not (tmp_path / "example.mindmap.html").exists()  # the map is the mindmap skill's job


def test_tsv_fallback_without_genanki(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def no_genanki(name, *args, **kwargs):
        if name == "genanki":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_genanki)
    msg = deck.write_anki(NODES, "Study", tmp_path / "s.apkg")
    assert "genanki not installed" in msg
    assert len((tmp_path / "s.tsv").read_text(encoding="utf-8").splitlines()) == 2
