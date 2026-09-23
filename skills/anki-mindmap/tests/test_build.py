"""Tests for the anki-mindmap core renderer (build.py)."""
from __future__ import annotations

import builtins
import importlib.util
import json
from pathlib import Path

import pytest

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


def test_note_guid_survives_editing_the_card_text():
    deck1 = build.build_deck(NODES, "Study")
    edited = [dict(NODES[0], card_back="Rewritten answer."), NODES[1]]
    deck2 = build.build_deck(edited, "Study")
    assert [n.guid for n in deck1.notes] == [n.guid for n in deck2.notes]


def test_note_guid_differs_across_decks_for_same_node_id():
    g1 = build.build_deck(NODES, "Deck A").notes[0].guid
    g2 = build.build_deck(NODES, "Deck B").notes[0].guid
    assert g1 != g2


def test_build_deck_uses_per_name_deck_id():
    assert build.build_deck(NODES, "Deck A").deck_id == build.deck_id_for("Deck A")


# --- validation --------------------------------------------------------------------

def test_load_graph_rejects_unknown_evidence(tmp_path):
    bad = [dict(NODES[0], evidence="vibes")]
    with pytest.raises(SystemExit):
        build.load_graph(_write(tmp_path, bad))


def test_load_graph_rejects_duplicate_ids(tmp_path):
    with pytest.raises(SystemExit):
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


def test_build_py_stays_under_400_lines():
    assert len((SKILL_DIR / "build.py").read_text(encoding="utf-8").splitlines()) < 400


def test_mindmap_labels_carry_evidence(tmp_path):
    out = tmp_path / "s.mindmap.html"
    build.write_mindmap(NODES, "Study", out)
    md = out.with_suffix(".md").read_text(encoding="utf-8")
    assert "CLS token `shown`" in md


# --- regression + fallback -----------------------------------------------------------

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
