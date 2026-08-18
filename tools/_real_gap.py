"""Dump leftover English after stripping loc tokens."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
EN_RAW = ROOT / "loc" / "en" / "cards_en_raw.csv"
EN_LUA = ROOT / "loc" / "en" / "lua_cards.csv"
OUT = ROOT / "state" / "real_gap.json"

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z][A-Za-z']{1,}")


def strip_markup(text: str) -> str:
    text = re.sub(r"\$\{[^}]+\}", " ", text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return text


def leftover(text: str) -> list[str]:
    return LATIN.findall(strip_markup(text))


def load_raw() -> dict[str, str]:
    out = {}
    with EN_RAW.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                out[row[0]] = row[1]
    return out


raw = load_raw()
zh_map = {}
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for k, v in csv.reader(f):
        zh_map[k] = v

name_en = []
effect_left = []
flavor_en = []
word_freq = Counter()
prefix_left = Counter()

for key, zh in zh_map.items():
    words = leftover(zh)
    p = key.split("_", 1)[0]
    if key.startswith("CARDNAME_"):
        if words:
            name_en.append({"key": key, "en": strip_markup(raw.get(key, "")), "zh": zh})
            prefix_left[p] += 1
    elif key.startswith("FLAVOR_"):
        if words or not CJK.search(zh or ""):
            flavor_en.append({"key": key, "en": raw.get(key, ""), "zh": zh[:80]})
            prefix_left[p] += 1
    elif p in {"EFFECT", "FATE", "TROPHY", "ENERGY", "DAY", "NIGHT", "LABEL"}:
        if words:
            prefix_left[p] += 1
            for w in words:
                word_freq[w.lower()] += 1
            if len(effect_left) < 40:
                effect_left.append({"key": key, "zh": zh, "left": words})

lua_names = []
with EN_LUA.open(encoding="utf-8", newline="") as f:
    en_rows = list(csv.DictReader(f))

zh_lua = {}
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        zh_lua[row["id"]] = row

lua_left_names = []
lua_left_effects = 0
for row in en_rows:
    z = zh_lua.get(row["id"], {})
    if leftover(z.get("display_name") or ""):
        lua_left_names.append(
            {
                "id": row["id"],
                "set": row.get("card_set"),
                "en": row.get("display_name"),
                "zh": z.get("display_name"),
            }
        )
    if leftover(z.get("effect_text") or ""):
        lua_left_effects += 1

payload = {
    "cardname_left": len(name_en),
    "flavor_left": len(flavor_en),
    "prefix_left": dict(prefix_left),
    "effect_word_freq": word_freq.most_common(50),
    "effect_samples": effect_left,
    "lua_name_left": len(lua_left_names),
    "lua_effect_left": lua_left_effects,
    "names": name_en,
    "flavors": [{"key": r["key"], "en": r["en"]} for r in flavor_en],
    "lua_names": lua_left_names,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("cardname", len(name_en), "flavor", len(flavor_en), "lua names", len(lua_left_names), "lua effects", lua_left_effects)
print("prefix", dict(prefix_left))
print("top words", word_freq.most_common(30))
