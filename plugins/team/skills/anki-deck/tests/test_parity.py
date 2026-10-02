"""Drift guard for the copies that keep each skill standalone.

anki-deck and mindmap each ship their own concept_graph.py + SCHEMA.md (skills are installed
one by one, so neither may import the other). The colour-vision matrices live in Python here and
in JavaScript in easy-read. When the sibling skills sit next to this one (the repo), the copies
must be identical; when this skill is installed alone, the checks skip.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILLS = SKILL_DIR.parent
MINDMAP = SKILLS / "mindmap"
EASY_READ_JS = SKILLS / "easy-read" / "easy-read.js"


@pytest.mark.skipif(not MINDMAP.is_dir(), reason="mindmap skill not installed alongside")
@pytest.mark.parametrize("name", ["concept_graph.py", "SCHEMA.md"])
def test_shared_copies_are_identical(name):
    ours = (SKILL_DIR / name).read_text(encoding="utf-8")
    theirs = (MINDMAP / name).read_text(encoding="utf-8")
    assert ours == theirs, f"{name} drifted: edit both copies together"


@pytest.mark.skipif(not EASY_READ_JS.is_file(), reason="easy-read skill not installed alongside")
def test_cvd_matrices_match_easy_read():
    sys.path.insert(0, str(SKILL_DIR))
    from build_deck import CVD_MATRICES  # noqa: E402

    js = EASY_READ_JS.read_text(encoding="utf-8")
    block = re.search(r"var CVD = \{(.*?)\};", js, re.S)
    assert block, "easy-read.js has no CVD matrix table"
    js_matrices = dict(re.findall(r'"([a-z-]+)":\s*"([-0-9. ]+)"', block.group(1)))
    assert js_matrices == CVD_MATRICES
