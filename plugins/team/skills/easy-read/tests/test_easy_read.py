"""Static checks for easy-read.js (no browser): syntax, controls, and the no-svg rule."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parents[1] / "easy-read.js"
SRC = JS.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_widget_is_valid_javascript():
    subprocess.run(["node", "--check", str(JS)], check=True)


@pytest.mark.parametrize("control", ['"font"', '"size"', '"lh"', '"ls"', '"scheme"', '"bionic"',
                                     '"focus"', '"hl"', '"cvd"'])
def test_every_setting_has_a_control(control):
    assert control in SRC


def test_colour_vision_offers_both_daltonisation_modes():
    assert '"red-green"' in SRC and '"blue-yellow"' in SRC
    assert "feColorMatrix" in SRC and 'color-interpolation-filters' in SRC


def test_colour_vision_filters_the_root_element():
    # on <html>: the root is the only element whose filter does not re-anchor position:fixed
    # descendants (sticky headers, modals, the panel itself)
    assert "html.er-cvd{filter:url(#er-cvd)}" in SRC
    assert "body > :not(.er-ui){filter" not in SRC


def test_colour_vision_is_off_by_default():
    assert 'cvd: ""' in SRC.split("var DEFAULTS")[1].split(";")[0]


def test_widget_never_edits_svg_text():
    assert 'var SKIP = "svg,' in SRC and ":not(svg *)" in SRC


def test_storage_access_is_guarded():
    calls = SRC.count("localStorage.getItem") + SRC.count("localStorage.setItem")
    guarded = SRC.count("try { return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem")
    guarded += SRC.count("try { localStorage.setItem")
    assert calls == guarded == 2


def test_lexiad_is_local_only():
    assert 'local("Lexiad")' in SRC and ".ttf" not in SRC
