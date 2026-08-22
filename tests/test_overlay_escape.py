# -*- coding: utf-8 -*-
"""Regression: overlay escape/unescape must not leave double-escaped \\r."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from overlay import escape  # noqa: E402


def test_escape_does_not_double_escape_literal_cr_sequences():
    raw = "<margin-right=8em>\\rYou need Runes to acquire Heroes."
    out = escape(raw)
    assert "\\\\r" not in out
    assert "\\r" not in out  # real CR normalized to \\n
    assert "\\n" in out or "You need Runes" in out.replace("\\n", "\n")


def test_escape_roundtrip_matches_game_norm():
    game = (
        "<margin-right=8em>\rYou need Runes to acquire Heroes and Constructs.  "
        "Runes come from Heroes played from your hand or from Constructs you have in play.  "
        "You may acquire any number of cards as long as you have enough Runes.  "
        "Cards that are eligible to be acquired will glow green.\n\n"
    )
    csv_form = game.replace("\r", "\\r").replace("\n", "\\n")
    escaped = escape(csv_form)

    def unescape_plugin(s: str) -> str:
        s = s.replace("\\\\r\\\\n", "\n").replace("\\\\r", "\n").replace("\\\\n", "\n")
        s = s.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n").replace("\\t", "\t")
        return s.replace("\\\\", "\\")

    def norm(s: str) -> str:
        s = re.sub(r"<[^>]*>", " ", s)
        s = s.replace("\\", " ")
        s = re.sub(r"\s+", " ", s).strip().lower()
        return s

    assert norm(unescape_plugin(escaped)) == norm(game)


def test_overlay_tsv_no_double_backslash_r():
    ov = (ROOT / "loc" / "zh-Hans" / "overlay.tsv").read_text(encoding="utf-8")
    # After rebuild, rulebook keys must not contain \\\\r
    assert "\\\\\\\\r" not in ov
    # Single-escaped \\r in file is OK as two-char sequence in text... check raw
    bad = [line[:80] for line in ov.splitlines() if "\\\\r" in line or line.count("\\r") and "\\\\rYou" in line]
    # Accept \\n escapes; reject \\\\r (double)
    doubles = [ln for ln in ov.splitlines() if "\\\\r" in ln]
    assert not doubles, f"double-escaped CR still present: {doubles[:3]}"
