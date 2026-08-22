# -*- coding: utf-8 -*-
"""Phase 2: retranslate machine card effects/names and promote clean rows."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from inventory_build import _machine_mixed  # noqa: E402
from translate import translate_effect, translate_flavor, translate_name  # noqa: E402

ZH_LUA = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
EN_LUA = ROOT / "loc" / "en" / "lua_cards.csv"
WORD = re.compile(r"[A-Za-z][A-Za-z']{1,}")

# Keyword / typo cleanup after phrase translation.
POST_REPLACEMENTS: list[tuple[str, str]] = [
    ("传送门牌库", "中央牌库"),  # historical mistranslation of center deck
    ("ENERGIZE", "充能"),
    ("EMPOWER", "赋力"),
    ("DREAMBIND", "梦缚"),
    ("INFEST", "感染"),
    ("ONGOING", "持续"),
    ("EVENT", "事件"),
    ("SERENITY", "宁静"),
    ("ECHO", "回响"),
    ("Echo", "回响"),
    ("PHANTASM", "幻象"),
    ("TRANSFORM", "转化"),
    ("Renown", "声望"),
    ("renown", "声望"),
    ("Reward:", "奖励："),
    ("reward:", "奖励："),
    ("Reward", "奖励"),
    ("Replace", "替换"),
    ("Remove", "移除"),
    ("Shuffle", "洗牌"),
    ("Return", "返回"),
    ("Double", "翻倍"),
    ("facedown", "面朝下"),
    ("face down", "面朝下"),
    ("face-down", "面朝下"),
    ("you've", "你已"),
    ("you're", "你"),
    ("you've", "你已"),
    ("win the game", "赢得游戏"),
    ("win game", "赢得游戏"),
    ("Giant Rats", "巨鼠"),
    ("Giant Rat", "巨鼠"),
    ("Rats", "巨鼠"),
    ("Rat King", "鼠王"),
    ("Rat ", "巨鼠 "),
    ("Ring of Life", "生命之戒"),
    ("Arha Sanctuary", "亚哈圣所"),
    ("Arha", "亚哈"),
    ("Constuct", "神器"),
    ("desroys", "摧毁"),
    ("aand", "和"),
    ("anyhere", "任何地方"),
    ("anywhere", "任何地方"),
    ("non-", "非"),
    ("DAY", "昼"),
    ("NIGHT", "夜"),
    ("Faction", "派系"),
    ("Temples", "神殿"),
    ("Temple", "神殿"),
    ("monsters", "怪物"),
    ("monster", "怪物"),
    ("Heroes", "英雄"),
    ("heroes", "英雄"),
    ("Hero", "英雄"),
    ("hero", "英雄"),
    ("decks", "牌库"),
    ("deck", "牌库"),
    ("space", "空位"),
    ("spaces", "空位"),
    ("swap", "交换"),
    ("rep", "声望"),
    ("Value", "数值"),
    ("value", "数值"),
    ("type", "类型"),
    ("choice", "选择"),
    ("text", "文本"),
    ("half", "一半"),
    ("total", "总计"),
    ("least", "至少"),
    ("start", "开始"),
    ("goes", "变为"),
    ("move", "移动"),
    ("before", "之前"),
    ("already", "已经"),
    ("round", "回合"),
    ("does", "会"),
    ("use", "使用"),
    ("loses", "失去"),
    ("set", "设置"),
    ("get", "获得"),
    (" eight", " 8"),
    ("eight ", "8 "),
]


def _post_clean(text: str) -> str:
    out = text
    for en, zh in sorted(POST_REPLACEMENTS, key=lambda x: len(x[0]), reverse=True):
        out = out.replace(en, zh)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r" +([，。；：])", r"\1", out)
    return out.strip()


def _has_latin(text: str) -> bool:
    return bool(WORD.search(text or ""))


def _load_en() -> dict[str, dict[str, str]]:
    with EN_LUA.open(encoding="utf-8", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def run(*, write: bool = True) -> dict[str, int]:
    en_by_id = _load_en()
    with ZH_LUA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    stats = {
        "machine_total": 0,
        "effect_updated": 0,
        "name_updated": 0,
        "flavor_updated": 0,
        "promoted": 0,
        "still_dirty": 0,
    }
    dirty: list[str] = []

    for r in rows:
        if (r.get("source") or "") != "machine":
            continue
        stats["machine_total"] += 1
        e = en_by_id.get(r["id"])
        if not e:
            stats["still_dirty"] += 1
            dirty.append(r["id"])
            continue

        new_effect = _post_clean(translate_effect(e.get("effect_text") or ""))
        new_name = _post_clean(translate_name(e.get("display_name") or e.get("card_name") or r["id"]))
        en_flavor = (e.get("flavor_text") or "").strip()
        new_flavor = r.get("flavor_text") or ""
        if en_flavor:
            new_flavor = _post_clean(translate_flavor(en_flavor))

        if new_effect and new_effect != (r.get("effect_text") or ""):
            r["effect_text"] = new_effect
            stats["effect_updated"] += 1
        else:
            r["effect_text"] = new_effect or r.get("effect_text") or ""

        if new_name and new_name != (r.get("display_name") or ""):
            r["display_name"] = new_name
            stats["name_updated"] += 1
        elif new_name:
            r["display_name"] = new_name

        if en_flavor and new_flavor:
            if new_flavor != (r.get("flavor_text") or ""):
                stats["flavor_updated"] += 1
            r["flavor_text"] = new_flavor

        blob = "\n".join(
            [
                r.get("display_name") or "",
                r.get("effect_text") or "",
                r.get("flavor_text") or "",
            ]
        )
        if _machine_mixed(blob) or _has_latin(r.get("effect_text") or ""):
            stats["still_dirty"] += 1
            dirty.append(r["id"])
        else:
            r["source"] = "community"
            stats["promoted"] += 1

    if write:
        with ZH_LUA.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        dirty_path = ROOT / "loc" / "inventory" / "phase2_dirty_ids.txt"
        dirty_path.write_text("\n".join(dirty) + ("\n" if dirty else ""), encoding="utf-8")

    print(stats)
    print("sample dirty:", dirty[:12])
    return stats


if __name__ == "__main__":
    run(write="--dry" not in sys.argv)
