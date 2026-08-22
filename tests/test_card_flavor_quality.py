# -*- coding: utf-8 -*-
"""Regression: cards.csv FLAVOR must not be mixed EN/ZH garbage."""
from __future__ import annotations

import re
from pathlib import Path

from conftest import ROOT

CARDS = ROOT / "loc" / "zh-Hans" / "cards.csv"


def test_no_mixed_flavor_machine_garbage():
    mixed = []
    for line in CARDS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("FLAVOR_") or "," not in line:
            continue
        k, rest = line.split(",", 1)
        zh = rest.strip().strip('"').replace('""', '"')
        plain = re.sub(r"<[^>]+>|\$\{[^}]+\}", " ", zh)
        if re.search(r"[\u4e00-\u9fff]", plain) and re.search(r"[A-Za-z]{3,}", plain):
            mixed.append(k)
    assert not mixed, f"mixed FLAVOR rows (sample): {mixed[:10]}"


def test_arbiter_flavor_is_chinese():
    blob = CARDS.read_text(encoding="utf-8")
    assert "FLAVOR_ARBITEROFTHEPRECIPICE," in blob
    line = [l for l in blob.splitlines() if l.startswith("FLAVOR_ARBITEROFTHEPRECIPICE,")][0]
    assert "记忆与历史" in line
    assert "Memory" not in line


def test_achievements_runtime_present():
    rt = (ROOT / "loc" / "zh-Hans" / "ui_runtime.csv").read_text(encoding="utf-8")
    for s in ("On Your Way", "First Beatdown", "Win a game.", "Achievements"):
        assert s in rt
