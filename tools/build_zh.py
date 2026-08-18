"""Build zh-Hans lua_cards.csv from extracted English + glossary + overrides."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GLOSSARY = ROOT / "glossary" / "terms.csv"
OVERRIDES = ROOT / "loc" / "zh-Hans" / "overrides.csv"
EN_CARDS = ROOT / "loc" / "en" / "lua_cards.csv"
OUT = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"

# Longest-first phrase replacements applied to leftover English effect text.
EFFECT_PHRASES = [
    ("Once per turn, ", "每回合一次，"),
    ("once per turn, ", "每回合一次，"),
    ("without paying its cost", "无需支付费用"),
    ("without paying", "无需支付"),
    ("in the center row", "在中央牌列"),
    ("in your hand or discard pile", "在你的手牌或弃牌堆"),
    ("in your discard pile", "在你的弃牌堆"),
    ("in your hand", "在你的手牌中"),
    ("on top of your deck", "放到你的牌库顶"),
    ("into your discard pile", "置入你的弃牌堆"),
    ("into play", "进入战场"),
    ("Draw three cards", "抽三张牌"),
    ("Draw two cards", "抽两张牌"),
    ("Draw a card", "抽一张牌"),
    ("draw two cards", "抽两张牌"),
    ("draw a card", "抽一张牌"),
    ("this turn", "本回合"),
    ("this Hero", "此英雄"),
    ("this Construct", "此神器"),
    ("Mechana Construct", "机械神器"),
    ("Lifebound Hero", "生命英雄"),
    ("Enlightened Hero", "启迪英雄"),
    ("Void Hero", "虚空英雄"),
    ("center row", "中央牌列"),
    ("discard pile", "弃牌堆"),
    ("Honor tokens", "荣誉点数"),
    ("honor tokens", "荣誉点数"),
    ("You may ", "你可以"),
    ("you may ", "你可以"),
    ("Gain ", "获得"),
    ("gain ", "获得"),
    ("Defeat a Monster", "击败一个怪物"),
    ("Defeat a ", "击败一个"),
    ("Banish a card", "放逐一张卡牌"),
    ("Banish a ", "放逐一个"),
    ("Acquire a Hero", "获取一个英雄"),
    ("Acquire a ", "获取一个"),
    ("Reward: ", "奖励："),
    ("that has P", "战力值不高于"),
    ("or less", "或更低"),
    ("or more", "或更高"),
]


def load_glossary() -> list[tuple[str, str]]:
    rows = []
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            en = (row.get("english") or "").strip()
            zh = (row.get("zh_hans") or "").strip()
            if en and zh:
                rows.append((en, zh))
    rows.sort(key=lambda x: len(x[0]), reverse=True)
    return rows


def load_overrides() -> dict[str, dict[str, str]]:
    if not OVERRIDES.is_file():
        return {}
    with OVERRIDES.open(encoding="utf-8", newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def translate_effect(text: str, glossary: list[tuple[str, str]]) -> str:
    if not text:
        return ""
    out = text
    for en, zh in EFFECT_PHRASES:
        out = out.replace(en, zh)
    # Compact resource tokens used in Lua (not TMP icons)
    out = re.sub(r"(\d+)R\b", r"\1符文", out)
    out = re.sub(r"(\d+)P\b", r"\1战力", out)
    out = re.sub(r"(\d+)H\b", r"\1荣誉", out)
    out = re.sub(r"(\d+)I\b", r"\1洞察", out)
    for en, zh in glossary:
        if len(en) < 3:
            continue
        out = re.sub(rf"\b{re.escape(en)}\b", zh, out)
    return out


def main() -> None:
    glossary = load_glossary()
    name_map = {en.lower(): zh for en, zh in glossary}
    overrides = load_overrides()
    rows = []
    with EN_CARDS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ov = overrides.get(row["id"], {})
            if not ov:
                # Reuse base-set overrides for 10TH / SoS / RoV / RU clones.
                base_id = re.sub(r" (10TH|SoS|RoV|RU)$", "", row["id"])
                if base_id != row["id"]:
                    ov = dict(overrides.get(base_id, {}))
                    if ov.get("source"):
                        ov["source"] = ov["source"] + "+variant"
            display = ov.get("display_name") or name_map.get(row["display_name"].lower()) or ""
            effect = ov.get("effect_text") or translate_effect(row["effect_text"], glossary)
            flavor = ov.get("flavor_text") or ""
            source = ov.get("source") or ("glossary" if display else "draft")
            rows.append(
                {
                    "id": row["id"],
                    "card_set": row.get("card_set", ""),
                    "display_name": display or row["display_name"],
                    "effect_text": effect,
                    "flavor_text": flavor,
                    "source": source,
                }
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "card_set", "display_name", "effect_text", "flavor_text", "source"],
        )
        w.writeheader()
        w.writerows(rows)
    named = sum(1 for r in rows if r["source"] != "draft" or r["display_name"] != "")
    print(f"wrote {OUT} ({len(rows)} cards)")


if __name__ == "__main__":
    main()
