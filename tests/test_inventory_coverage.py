# -*- coding: utf-8 -*-
"""L1: inventory coverage gates (ceilings must not worsen)."""

from __future__ import annotations

import csv
import json
import subprocess
import sys

from conftest import INVENTORY, ROOT


def _load_gates() -> dict:
    path = INVENTORY / "gates.json"
    assert path.is_file(), "gates.json missing — run python tools/inventory_build.py"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_summary() -> dict:
    path = INVENTORY / "summary.json"
    assert path.is_file(), "summary.json missing — run python tools/inventory_build.py"
    return json.loads(path.read_text(encoding="utf-8"))


def test_inventory_rebuild_is_deterministic_enough():
    """Rebuild inventory; script must exit 0."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "inventory_build.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stdout + "\n" + r.stderr


def test_required_domains_present():
    gates = _load_gates()
    summary = _load_summary()
    present = set(summary["by_domain"].keys())
    required = set(gates["required_domains"])
    missing_domains = required - present
    assert not missing_domains, f"inventory lost domains: {missing_domains}"


def test_missing_counts_do_not_exceed_ceilings():
    gates = _load_gates()
    summary = _load_summary()
    assert summary["missing_total"] <= gates["max_missing_total"], (
        f"missing_total rose: {summary['missing_total']} > {gates['max_missing_total']}"
    )
    ceilings = gates.get("max_missing_by_domain") or {}
    for domain, ceiling in ceilings.items():
        actual = int(summary["by_domain"].get(domain, {}).get("missing", 0))
        assert actual <= int(ceiling), (
            f"domain {domain} missing rose: {actual} > {ceiling}"
        )


def test_draft_counts_do_not_exceed_ceilings():
    gates = _load_gates()
    summary = _load_summary()
    if "max_draft_total" not in gates:
        return
    assert summary["draft_total"] <= gates["max_draft_total"], (
        f"draft_total rose: {summary['draft_total']} > {gates['max_draft_total']}"
    )
    ceilings = gates.get("max_draft_by_domain") or {}
    for domain, ceiling in ceilings.items():
        actual = int(summary["by_domain"].get(domain, {}).get("draft", 0))
        assert actual <= int(ceiling), (
            f"domain {domain} draft rose: {actual} > {ceiling}"
        )


def test_waived_rows_have_reasons():
    path = INVENTORY / "strings.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    bad = [
        r["id"]
        for r in rows
        if r.get("status") == "waived" and not (r.get("waived_reason") or "").strip()
    ]
    assert not bad, f"waived without reason: {bad[:10]}"


def test_rulebook_csv_row_count_stable():
    """Rulebook ledger must stay registered (93 rows historically)."""
    rb = ROOT / "loc" / "zh-Hans" / "rulebook.csv"
    with rb.open(encoding="utf-8", newline="") as f:
        n = sum(1 for _ in csv.DictReader(f))
    assert n >= 90, f"rulebook.csv unexpectedly small: {n}"
