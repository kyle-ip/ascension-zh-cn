# -*- coding: utf-8 -*-
"""L2: glossary terminology gates."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict

from conftest import GLOSSARY, INVENTORY, ZH


def _gates() -> dict:
    return json.loads((INVENTORY / "gates.json").read_text(encoding="utf-8"))


def _approved_glossary() -> list[dict[str, str]]:
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        return [
            r
            for r in csv.DictReader(f)
            if (r.get("status") or "").strip() == "approved"
            and (r.get("en") or "")
            and not (r.get("en") or "").startswith("#")
        ]


def test_enlightened_maps_to_shengxian():
    gates = _gates()
    require = gates.get("require_glossary_en") or {}
    rows = _approved_glossary()
    by_en = {r["en"]: r["zh"] for r in rows}
    for en, zh in require.items():
        assert en in by_en, f"glossary missing approved en={en!r}"
        assert zh in by_en[en], f"glossary {en!r} expected to contain {zh!r}, got {by_en[en]!r}"


def test_approved_glossary_no_duplicate_en_scope_conflict():
    """Same (en, scope) must not have two different zh among approved rows."""
    buckets: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in _approved_glossary():
        buckets[(r["en"], r.get("scope") or "")].add(r.get("zh") or "")
    conflicts = {k: v for k, v in buckets.items() if len(v) > 1}
    assert not conflicts, f"glossary conflicts: {list(conflicts.items())[:5]}"


def test_forbid_qidi_in_glossary_approved_faction():
    """Enlightened must not be 启迪 in approved glossary."""
    for r in _approved_glossary():
        if r["en"] == "Enlightened" and (r.get("scope") or "") == "faction":
            assert "启迪" not in (r.get("zh") or ""), r


def test_lua_cards_forbid_terms_ceiling():
    """启迪 count in lua_cards must not rise above baseline gate."""
    gates = _gates()
    forbid = gates.get("forbid_glossary_terms_in_zh") or ["启迪"]
    ceilings = gates.get("max_forbid_term_hits") or {}
    text = (ZH / "lua_cards.csv").read_text(encoding="utf-8")
    for term in forbid:
        hits = text.count(term)
        assert term in ceilings, (
            f"gates.json missing max_forbid_term_hits[{term!r}] — "
            "re-run python tools/inventory_build.py"
        )
        ceiling = int(ceilings[term])
        assert hits <= ceiling, f"{term!r} hits rose: {hits} > {ceiling}"
