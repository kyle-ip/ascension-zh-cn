"""List leftover name words."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / "loc" / "en" / "lua_cards.csv"
ZH = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
LATIN = re.compile(r"[A-Za-z][A-Za-z']*")

zh = {}
with ZH.open(encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        zh[r["id"]] = r["display_name"]

words = Counter()
names = []
with EN.open(encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        z = zh.get(r["id"], "")
        if LATIN.search(z or ""):
            en = r["display_name"]
            names.append(en)
            for w in LATIN.findall(en):
                words[w] += 1

print("leftover names", len(names), "unique", len(set(names)))
print("unique words", len(words))
for w, c in words.most_common():
    print(f"{c:3} {w}")
