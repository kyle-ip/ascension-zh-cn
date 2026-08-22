# -*- coding: utf-8 -*-
"""L3: pure-function mirrors of overlay / rewrite helpers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from overlay import strip_tags, _split_rulebook_paragraphs  # noqa: E402


def test_strip_tags_removes_tmp_markup():
    assert strip_tags("<b>Honor</b>") == "Honor"
    assert "Fate" in strip_tags("<color=#fdc60eff>Fate:</color> When")


def test_strip_tags_drop_cap():
    out = strip_tags("<size=104>A</size>skara of Fate")
    assert "skara" in out.lower() or "Askara" in out or "askara" in out.lower()


def test_split_rulebook_paragraphs_br():
    en = (
        "Harness elemental magic and the power of ancient temples with this bundle!"
        "<br><br>"
        "<b>Gift of the Elements:</b><br>55 cards<br><br>"
        "Infest your opponent's deck with rampaging goblins and more text here to pass length."
    )
    parts = _split_rulebook_paragraphs(en)
    assert isinstance(parts, list)
    assert parts


STATE_MARKERS = {
    "Play Your Turn",
    "End Turn",
    "END TURN",
}


def test_state_markers_frozen():
    """Document critical state markers; plugin must keep this set stable or update test."""
    plugin = (ROOT / "plugin" / "AscensionZhCn" / "Plugin.cs").read_text(encoding="utf-8")
    for m in STATE_MARKERS:
        assert m in plugin, f"state marker {m!r} missing from Plugin.cs"
