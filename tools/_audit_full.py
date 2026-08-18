"""Write a JSON gap inventory. ASCII-only stdout."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
EN = ROOT / "loc" / "en"
SHEETS = EN / "sheets"
OUT = ROOT / "state" / "translation_gap.json"

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{3,}")
SKIP_WORDS = {
    "THE", "AND", "FOR", "YOU", "THIS", "THAT", "WITH", "FROM", "INTO", "YOUR",
    "WHEN", "ARE", "NOT", "ALL", "ANY", "MAY", "CAN", "HAS", "HAVE", "ITS",
    "ICON", "LABEL", "SPRITE", "SIZE", "COLOR", "BR", "HTML", "TRUE", "FALSE",
    "OK", "TMP",
}


def leftover_words(text: str) -> list[str]:
    out = []
    for w in LATIN.findall(text or ""):
        u = w.upper()
        if u in SKIP_WORDS:
            continue
        if w.startswith("ICON") or w.startswith("LABEL"):
            continue
        out.append(w)
    return out


def has_cjk(text: str) -> bool:
    return bool(CJK.search(text or ""))


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


lua_src = Counter()
lua_name_en_by_set = Counter()
lua_effect_en_by_set = Counter()
lua_leftover_names: dict[str, list[dict]] = defaultdict(list)
lua_mixed_effects: dict[str, list[dict]] = defaultdict(list)
lua_n = 0
lua_flavor_empty = 0
lua_name_cjk = 0
lua_effect_cjk = 0

with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        lua_n += 1
        src = row.get("source") or "empty"
        cset = row.get("card_set") or "?"
        lua_src[src] += 1
        name = row.get("display_name") or ""
        effect = row.get("effect_text") or ""
        flavor = row.get("flavor_text") or ""
        if has_cjk(name):
            lua_name_cjk += 1
        if leftover_words(name):
            lua_name_en_by_set[cset] += 1
            lua_leftover_names[cset].append(
                {"id": row["id"], "name": name, "source": src}
            )
        if has_cjk(effect):
            lua_effect_cjk += 1
        if leftover_words(effect):
            lua_effect_en_by_set[cset] += 1
            if len(lua_mixed_effects[cset]) < 8:
                lua_mixed_effects[cset].append(
                    {"id": row["id"], "effect": effect[:180], "source": src}
                )
        if not flavor.strip():
            lua_flavor_empty += 1

pref = Counter()
cjk = Counter()
latin_only = Counter()
mixed = Counter()
card_rows: dict[str, list[dict]] = defaultdict(list)
effect_word_freq = Counter()

with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        p = key.split("_", 1)[0]
        pref[p] += 1
        words = leftover_words(val)
        cjk_ok = has_cjk(val)
        if cjk_ok:
            cjk[p] += 1
        if words and not cjk_ok:
            latin_only[p] += 1
            card_rows[p].append({"key": key, "en": val})
        elif words and cjk_ok:
            mixed[p] += 1
            if p == "EFFECT":
                for w in words:
                    effect_word_freq[w.lower()] += 1
            if p == "LABEL":
                card_rows["LABEL_MIXED"].append({"key": key, "zh": val})
        if p == "FLAVOR" and words and not cjk_ok:
            pass  # already in latin_only

en_ui = load_two_col(SHEETS / "Common_Strings.csv")
zh_ui = load_dict(ZH / "ui.csv", "key", "zh")
ui_missing = []
ui_still = []
for key, en in en_ui:
    zh = zh_ui.get(key, "")
    if not zh:
        ui_missing.append({"key": key, "en": en})
    elif zh.strip() == en.strip() or not has_cjk(zh):
        ui_still.append({"key": key, "en": en, "zh": zh})

ingame = []
for key, en in load_two_col(SHEETS / "Common_Ingame.csv"):
    zh = zh_ui.get(key, "")
    ingame.append(
        {
            "key": key,
            "en": en,
            "zh": zh,
            "ok": bool(zh and has_cjk(zh)),
        }
    )

tut_en = load_two_col(EN / "tutorial.csv")
tut_zh = dict(load_two_col(ZH / "tutorial.csv"))
tut_need = []
tut_prompt = []
for key, en in tut_en:
    zh = tut_zh.get(key, "")
    rec = {"key": key, "en": en[:160], "zh": (zh or "")[:160]}
    if key.startswith("TUTORIAL_PROMPT") or "${CLICK" in en or "${CLICK" in zh:
        tut_prompt.append(rec)
    elif leftover_words(zh) or not has_cjk(zh):
        tut_need.append(rec)

combat = load_two_col(ZH / "combat_log.csv")
runtime = load_two_col(ZH / "ui_runtime.csv")

# Overlay exact English strings still mapped (these are UI extras, already have zh)
overlay_exact = []
overlay_path = ZH / "overlay.tsv"
if overlay_path.is_file():
    with overlay_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[0] in {"E", "U"}:
                overlay_exact.append({"kind": parts[0], "en": parts[1], "zh": parts[2]})

# Flavor leftover names (join CARDNAME)
cardname_map = {}
flavor_map = {}
effect_map = {}
with (ZH / "cards.csv").open(encoding="utf-8", newline="") as f:
    for key, val in csv.reader(f):
        if key.startswith("CARDNAME_"):
            cardname_map[key[9:]] = val
        elif key.startswith("FLAVOR_"):
            flavor_map[key[7:]] = val
        elif key.startswith("EFFECT_"):
            effect_map[key[7:]] = val

flavor_leftover = []
for stem, val in flavor_map.items():
    if leftover_words(val) and not has_cjk(val):
        flavor_leftover.append(
            {
                "key": "FLAVOR_" + stem,
                "name": cardname_map.get(stem, stem),
                "en": val,
            }
        )

cardname_leftover = [
    {"key": "CARDNAME_" + stem, "en": val}
    for stem, val in cardname_map.items()
    if leftover_words(val) and not has_cjk(val)
]

# Join leftover names to lua set via display_name / id
lua_by_id = {}
lua_by_name = {}
with (ZH / "lua_cards.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        lua_by_id[row["id"]] = row
        lua_by_name[row["id"].lower()] = row
        lua_by_name[(row.get("display_name") or "").lower()] = row

# English names from loc/en/lua_cards
en_lua_name = {}
en_lua = EN / "lua_cards.csv"
if en_lua.is_file():
    with en_lua.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            en_lua_name[row["id"]] = row.get("display_name") or row["id"]

name_leftover_by_set = Counter()
name_leftover_grouped: dict[str, list[str]] = defaultdict(list)
for rec in cardname_leftover:
    en = rec["en"]
    # try match lua english id
    matched_set = "?"
    for lid, lrow in lua_by_id.items():
        en_name = en_lua_name.get(lid, lid)
        if en_name == en or lid == en:
            matched_set = lrow.get("card_set") or "?"
            break
    rec["set"] = matched_set
    name_leftover_by_set[matched_set] += 1
    name_leftover_grouped[matched_set].append(en)

# 10th anniversary names
tenth = [r for r in cardname_leftover if r["key"].endswith("10TH")]

payload = {
    "lua": {
        "total": lua_n,
        "source": dict(lua_src),
        "display_name_cjk": lua_name_cjk,
        "display_name_latin": sum(lua_name_en_by_set.values()),
        "display_name_latin_by_set": dict(lua_name_en_by_set),
        "effect_cjk": lua_effect_cjk,
        "effect_latin": sum(lua_effect_en_by_set.values()),
        "effect_latin_by_set": dict(lua_effect_en_by_set),
        "flavor_empty": lua_flavor_empty,
        "leftover_names": {k: v for k, v in lua_leftover_names.items()},
        "mixed_effect_samples": {k: v for k, v in lua_mixed_effects.items()},
    },
    "cards_csv": {
        "total_by_prefix": dict(pref),
        "has_cjk": dict(cjk),
        "latin_only": dict(latin_only),
        "mixed_cjk_and_latin": dict(mixed),
        "labels": [
            {"key": k, "zh": v}
            for k, v in load_two_col(ZH / "cards.csv")
            if k.startswith("LABEL_")
        ],
        "cardname_leftover_count": len(cardname_leftover),
        "cardname_leftover_by_set": dict(name_leftover_by_set),
        "cardname_leftover": name_leftover_grouped,
        "cardname_10th_count": len(tenth),
        "flavor_leftover_count": len(flavor_leftover),
        "flavor_leftover": flavor_leftover,
        "effect_leftover_words_top": effect_word_freq.most_common(40),
        "mixed_label_rows": card_rows.get("LABEL_MIXED", []),
    },
    "ui": {
        "common_strings": len(en_ui),
        "ui_csv": len(zh_ui),
        "missing": ui_missing,
        "still_en": ui_still,
        "ingame": ingame,
        "runtime_exact": [{"en": a, "zh": b} for a, b in runtime],
    },
    "tutorial": {
        "en": len(tut_en),
        "zh": len(tut_zh),
        "need": tut_need,
        "prompts_kept_english": tut_prompt,
    },
    "combat_log": [{"en": a, "zh": b} for a, b in combat],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT)
print("lua", lua_n, "name_latin", sum(lua_name_en_by_set.values()), "effect_latin", sum(lua_effect_en_by_set.values()))
print("CARDNAME leftover", len(cardname_leftover), dict(name_leftover_by_set))
print("FLAVOR leftover", len(flavor_leftover))
print("EFFECT mixed", mixed.get("EFFECT", 0), "latin_only", latin_only.get("EFFECT", 0))
print("ui still_en", len(ui_still), "missing", len(ui_missing))
print("tut need", len(tut_need), "prompts", len(tut_prompt))
print("lua leftover names by set", dict(lua_name_en_by_set))
