"""Audit remaining English / untranslated Ascension overlay coverage."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
EN = ROOT / "loc" / "en"
SHEETS = EN / "sheets"

LATIN = re.compile(r"[A-Za-z]{3,}")
SKIP_WORDS = {
    "THE", "AND", "FOR", "YOU", "THIS", "THAT", "WITH", "FROM", "INTO", "YOUR",
    "WHEN", "ARE", "NOT", "ALL", "ANY", "MAY", "CAN", "HAS", "HAVE", "ITS",
    "ICON", "LABEL", "SPRITE", "SIZE", "COLOR", "BR", "HTML", "TRUE", "FALSE",
}


def leftover_words(text: str) -> list[str]:
    out = []
    for w in LATIN.findall(text or ""):
        if w.upper() in SKIP_WORDS:
            continue
        if w.startswith("ICON") or w.startswith("LABEL"):
            continue
        out.append(w)
    return out


def load_two_col(path: Path) -> list[tuple[str, str]]:
    rows = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0] and row[0] not in {"key", "en"}:
                rows.append((row[0], row[1]))
    return rows


def load_dict(path: Path, k: str, v: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r[k]: r[v] for r in csv.DictReader(f) if r.get(k)}


print("==== lua_cards source ====")
src = Counter()
name_en = 0
effect_en = 0
flavor_empty = 0
flavor_en = 0
n = 0
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        n += 1
        src[row.get("source") or "empty"] += 1
        if leftover_words(row.get("display_name") or ""):
            name_en += 1
        if leftover_words(row.get("effect_text") or ""):
            effect_en += 1
        fl = row.get("flavor_text") or ""
        if not fl:
            flavor_empty += 1
        elif leftover_words(fl) or not any("\u4e00" <= c <= "\u9fff" for c in fl):
            flavor_en += 1
print("cards", n, dict(src))
print("display_name still has latin", name_en)
print("effect_text still has latin", effect_en)
print("flavor empty", flavor_empty, "flavor still english/latin", flavor_en)

print("\n==== cards.csv prefixes ====")
pref = Counter()
cjk = Counter()
latin_rows = Counter()
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        p = key.split("_", 1)[0]
        pref[p] += 1
        if any("\u4e00" <= c <= "\u9fff" for c in val):
            cjk[p] += 1
        elif leftover_words(val):
            latin_rows[p] += 1
print("total", dict(pref))
print("has CJK", dict(cjk))
print("latin leftover", dict(latin_rows))

print("\n==== Common_Strings vs ui.csv ====")
en_ui = load_two_col(SHEETS / "Common_Strings.csv")
zh_ui = load_dict(ZH / "ui.csv", "key", "zh")
missing = []
still_en = []
for key, en in en_ui:
    zh = zh_ui.get(key, "")
    if not zh:
        missing.append((key, en))
    elif zh.strip() == en.strip() or not any("\u4e00" <= c <= "\u9fff" for c in zh):
        still_en.append((key, en, zh))
print("Common_Strings", len(en_ui), "ui.csv", len(zh_ui))
print("missing keys", len(missing))
print("zh equals en or no CJK", len(still_en))
for key, en, zh in still_en[:40]:
    print(f"  STILL {key}: {en!r} -> {zh!r}")
for key, en in missing[:20]:
    print(f"  MISS {key}: {en!r}")

print("\n==== Common_Ingame ====")
ingame = load_two_col(SHEETS / "Common_Ingame.csv")
for key, en in ingame:
    zh = zh_ui.get(key, "")
    flag = "OK" if zh and any("\u4e00" <= c <= "\u9fff" for c in zh) else "NEED"
    print(f"  {flag} {key}: {en!r} -> {zh!r}")

print("\n==== tutorial ====")
tut_en = load_two_col(EN / "tutorial.csv")
tut_zh = load_two_col(ZH / "tutorial.csv")
tut_map = dict(tut_zh)
print("en", len(tut_en), "zh", len(tut_zh))
for key, en in tut_en:
    zh = tut_map.get(key, "")
    if key.startswith("TUTORIAL_PROMPT") or "${CLICK" in en or "${CLICK" in zh:
        print(f"  PROMPT {key}: en={en!r} zh={zh!r}")
    elif leftover_words(zh) or not any("\u4e00" <= c <= "\u9fff" for c in zh):
        print(f"  TUT {key}: {zh[:80]!r}")

print("\n==== overlay exact leftover sample ====")
runtime = ZH / "ui_runtime.csv"
print("ui_runtime rows", sum(1 for _ in runtime.open(encoding="utf-8")) - 1)
