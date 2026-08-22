# -*- coding: utf-8 -*-
"""Promote remaining machine cards whose name+effect are CJK-clean.

Phase 2 exit cares about effects; English flavor may remain draft.
Also strip leftover English flavor when the EN source flavor is empty or
when zh flavor is still pure Latin (keep empty rather than bad EN).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH_LUA = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
EN_LUA = ROOT / "loc" / "en" / "lua_cards.csv"
WORD = re.compile(r"[A-Za-z][A-Za-z']+")
CJK = re.compile(r"[\u4e00-\u9fff]")
ALLOW = {"P.R.I.M.E", "P.R.I.M.E.", "N.I.N.E", "N.I.N.E.", "Ascension"}


def latin_words(text: str) -> list[str]:
    out = []
    for w in WORD.findall(text or ""):
        if w in ALLOW or (w + ".") in ALLOW:
            continue
        out.append(w)
    return out


def main() -> None:
    en = {r["id"]: r for r in csv.DictReader(EN_LUA.open(encoding="utf-8", newline=""))}
    with ZH_LUA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    promoted = cleared_flavor = 0
    left = []
    for r in rows:
        if (r.get("source") or "") != "machine":
            continue
        name = r.get("display_name") or ""
        effect = r.get("effect_text") or ""
        flavor = r.get("flavor_text") or ""

        # Drop pure-English flavor leftovers (inventory will waive empty).
        en_flavor = (en.get(r["id"], {}).get("flavor_text") or "").strip()
        if flavor and latin_words(flavor) and not CJK.search(flavor):
            r["flavor_text"] = ""
            flavor = ""
            cleared_flavor += 1
        elif not en_flavor and flavor and latin_words(flavor):
            r["flavor_text"] = ""
            flavor = ""
            cleared_flavor += 1

        bad = latin_words(name) + latin_words(effect)
        if bad:
            left.append((r["id"], bad[:8], effect[:80]))
            continue
        if not CJK.search(effect) and not CJK.search(name):
            left.append((r["id"], ["no_cjk"], effect[:80]))
            continue
        r["source"] = "community"
        promoted += 1

    with ZH_LUA.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    machine_left = sum(1 for r in rows if (r.get("source") or "") == "machine")
    print(f"promoted={promoted} cleared_flavor={cleared_flavor} machine_left={machine_left}")
    for item in left[:20]:
        print("LEFT", item)


if __name__ == "__main__":
    main()
