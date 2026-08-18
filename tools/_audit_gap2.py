"""More leftover samples for the review."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ZH = Path(__file__).resolve().parent.parent / "loc" / "zh-Hans"
EN = Path(__file__).resolve().parent.parent / "loc" / "en"
LATIN = re.compile(r"[A-Za-z]{3,}")


def leftover(text: str) -> list[str]:
    return [w for w in LATIN.findall(text or "") if w.upper() not in {"THE", "AND", "FOR", "YOU", "THIS", "BR"}]


print("==== CARDNAME leftover samples ====")
n = 0
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        if key.startswith("CARDNAME_") and leftover(val) and not any("\u4e00" <= c <= "\u9fff" for c in val):
            print(key, val)
            n += 1
            if n >= 25:
                break
print("... printed", n)

print("\n==== LABEL rows ====")
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        if key.startswith("LABEL_"):
            print(key, val)

print("\n==== EFFECT leftover ====")
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        if key.startswith("EFFECT_") and leftover(val):
            print(key, val[:120])

print("\n==== lua display leftover by set ====")
by = Counter()
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        if leftover(row.get("display_name") or ""):
            by[row.get("card_set") or "(none)"] += 1
print(dict(by))

print("\n==== lua names with leftover (first 30) ====")
n = 0
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        dn = row.get("display_name") or ""
        if leftover(dn) and not any("\u4e00" <= c <= "\u9fff" for c in dn):
            print(row["id"], "|", dn, "|", row.get("card_set"), "|", row.get("source"))
            n += 1
            if n >= 30:
                break
