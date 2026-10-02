"""Concept-graph schema shared by the anki-deck and mindmap skills (see SCHEMA.md).

Each of those skills ships its own identical copy of this file, so either one works when it is
installed alone. Edit both copies together; anki-deck/tests/test_parity.py fails on drift.
"""
from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = ("shown", "plausible", "guess", "unverified")
MAX_POINTS = 3


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
        for key in ("group", "summary", "card_front", "card_back", "answer", "image"):
            if n.get(key) is not None and not isinstance(n[key], str):
                raise ValueError(f"node {n['id']!r} {key} must be a string.")
        points = n.get("points") or []
        if not _is_str_list(points) or len(points) > MAX_POINTS:
            raise ValueError(f"node {n['id']!r} points must be a list of at most {MAX_POINTS} strings.")
        if n["id"] in seen:
            raise ValueError(f"duplicate node id {n['id']!r} (ids must be unique per graph).")
        seen.add(n["id"])
        ev = n.get("evidence")
        if ev is not None and ev not in EVIDENCE:
            raise ValueError(f"node {n['id']!r} has evidence {ev!r}; use one of {EVIDENCE}.")
    return data


def load_graph(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "nodes" in data:
        data = data["nodes"]
    return validate_nodes(data)
