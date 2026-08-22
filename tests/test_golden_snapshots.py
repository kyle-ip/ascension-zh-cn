# -*- coding: utf-8 -*-
"""L4: golden English → Chinese snapshots (must not regress unintentionally)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from conftest import GLOSSARY, ROOT, ZH

GOLDEN = Path(__file__).resolve().parent / "golden" / "snapshots.json"


def _glossary_map() -> dict[str, str]:
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        return {
            r["en"]: r["zh"]
            for r in csv.DictReader(f)
            if (r.get("status") or "") == "approved" and r.get("en") and r.get("zh")
        }


def _ui_map() -> dict[str, str]:
    out = {}
    with (ZH / "ui.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0] not in {"key", "en"}:
                out[row[0]] = row[1]
    return out


def _ui_runtime_map() -> dict[str, str]:
    out = {}
    path = ZH / "ui_runtime.csv"
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("en"):
                out[row["en"]] = row.get("zh") or ""
    return out


def test_golden_snapshots():
    assert GOLDEN.is_file()
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    gloss = _glossary_map()
    ui = _ui_map()
    ui_rt = _ui_runtime_map()
    for case in data["cases"]:
        kind = case["kind"]
        src = case["en"]
        expect = case["zh"]
        if kind == "glossary":
            got = gloss.get(src)
        elif kind == "ui_key":
            got = ui.get(src)
        elif kind == "ui_runtime":
            got = ui_rt.get(src)
        else:
            raise AssertionError(f"unknown kind {kind}")
        assert got == expect, f"{kind} {src!r}: expected {expect!r}, got {got!r}"
