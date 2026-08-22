# -*- coding: utf-8 -*-
"""L0: overlay / TSV build invariants."""

from __future__ import annotations

import csv
from collections import Counter

from conftest import GLOSSARY, OVERLAY, ROOT, ZH


def test_overlay_tsv_exists_and_has_header_shape():
    assert OVERLAY.is_file(), "overlay.tsv missing — run tools/overlay.py / build_zh.py"
    lines = OVERLAY.read_text(encoding="utf-8-sig").splitlines()
    assert lines, "overlay.tsv empty"
    # Rows are K|E \t src \t zh
    bad = []
    kinds = Counter()
    for i, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            bad.append((i, line[:80]))
            continue
        if parts[0] not in {"K", "E"}:
            bad.append((i, line[:80]))
            continue
        kinds[parts[0]] += 1
    assert not bad, f"malformed overlay rows (first 5): {bad[:5]}"
    assert kinds["K"] > 100
    assert kinds["E"] > 100


def test_overlay_no_duplicate_conflicting_exact_keys():
    """Same English exact key must not map to two different zh values."""
    mapping: dict[str, str] = {}
    conflicts = []
    for line in OVERLAY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("E\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        en, zh = parts[1], parts[2]
        if not en or not zh:
            continue
        if en in mapping and mapping[en] != zh:
            conflicts.append((en[:60], mapping[en][:40], zh[:40]))
        else:
            mapping[en] = zh
    assert not conflicts, f"conflicting Exact entries (first 5): {conflicts[:5]}"


def test_glossary_csv_readable():
    assert GLOSSARY.is_file()
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        rows = list(reader)
    assert len(rows) > 100
    assert {"en", "zh", "scope", "status"} <= fieldnames


def test_tools_compile():
    import py_compile
    from pathlib import Path

    tools = ROOT / "tools"
    for path in tools.glob("*.py"):
        if path.name.startswith("_") and path.name not in {
            "_clean_runtime.py",
        }:
            # skip one-off diag scripts that may be incomplete
            if path.name.startswith("_unitypy") or path.name.startswith("_dump"):
                continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            # allow private scratch scripts to fail; public tools must compile
            if path.name.startswith("_"):
                continue
            raise AssertionError(f"compile failed: {path.name}: {e}") from e
