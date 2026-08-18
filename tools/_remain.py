"""Show remaining leftover English after rebuild."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
LATIN = re.compile(r"[A-Za-z][A-Za-z']*")


def strip_markup(text: str) -> str:
    text = re.sub(r"\$\{[^}]+\}", " ", text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def leftover(text: str) -> list[str]:
    return LATIN.findall(strip_markup(text))


print("==== CARDNAME leftover ====")
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        if k.startswith("CARDNAME_") and leftover(v):
            print(k, v)

print("==== LABEL leftover ====")
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        if k.startswith("LABEL_") and leftover(v):
            print(k, v)

print("==== lua names leftover ====")
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if leftover(r.get("display_name") or ""):
            print(r["id"], "|", r["display_name"])

print("==== EFFECT samples leftover ====")
n = 0
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        words = leftover(v)
        if k.startswith("EFFECT_") and words:
            print(k, words, v[:160])
            n += 1
            if n >= 25:
                break

print("==== FLAVOR leftover words ====")
freq = Counter()
n = 0
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        if not k.startswith("FLAVOR_"):
            continue
        words = leftover(v)
        if words:
            n += 1
            for w in words:
                freq[w.lower()] += 1
print("flavor rows with latin", n)
print(freq.most_common(40))
print("sample flavors:")
c = 0
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        if k.startswith("FLAVOR_") and leftover(v):
            print(v[:120])
            c += 1
            if c >= 8:
                break
