# -*- coding: utf-8 -*-
"""Apply hand-polished Phase 2 translations for leftover dirty machine cards."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH_LUA = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
WORD = re.compile(r"[A-Za-z][A-Za-z']+")
ALLOW_LATIN = {"P.R.I.M.E", "P.R.I.M.E.", "N.I.N.E", "N.I.N.E.", "Ascension"}

# Exact dirty ids from phase2_dirty_ids.txt → polished effects.
EFFECTS: dict[str, str] = {
    "Aether Warrior": "幻象——当此牌在中央牌列时，你可以支付5洞察放逐并打出此牌。\n抽两张牌。",
    "Arbiter Circlet": "每回合一次，获得1战力。",
    "Arha Emissary": "抽一张牌。\n若你本回合打出过每个派系的使者，你赢得游戏。",
    "Berserker Frenzy": "若你本回合已在中央牌列击败三个或更多怪物，你可以获取此牌且无需支付费用。\n获得10荣誉。\n持续：每回合一次，当你击败一个怪物时，将其荣誉奖励翻倍。",
    "Caaro, Desert Breaker": "奖励：获得4荣誉。对每位对手，你选择并摧毁其控制的一个神器。\n梦缚：2洞察。",
    "Cetra, Benefactor of All": "从你开始，按回合顺序，每位玩家获取一张英雄且无需支付费用。以此法获取的英雄置于其拥有者的牌库顶。",
    "Darktome Librarian": "获得2洞察。\n你可以放逐你手牌或弃牌堆中的一张牌。",
    "Demon Hunter": "当此牌在你手牌中时，你可以支付8洞察，将其转化为恶魔大师。\n获得2战力。",
    "Demon Master": "获得5战力。你可以放逐你手牌或弃牌堆中的一张牌。",
    "Demon Pups": "奖励：获得1荣誉。抽一张牌。然后你可以支付1洞察再抽一张牌。",
    "Dreadmare": "奖励：获得4荣誉和3洞察。",
    "Dream Chamber Disciples": "抽一张牌。\n宁静：获得2洞察。（若你的弃牌堆中没有卡牌，则获得此效果。）",
    "Dream Eater": "奖励：获得2荣誉和1洞察。",
    "Dream Guide": "获得2符文和1洞察。",
    "Dream Stone": "你可以放逐此牌以掷谵妄骰。",
    "Dream Titan": "奖励：获得6荣誉。",
    "Dream Tyrant": "奖励：获得5荣誉和5洞察。",
    "Dreamscape Diviner": "获得2洞察。",
    "Dreamscarred Hunter": "抽一张牌。\n掠夺——本回合若你获取一张卡牌并且击败一个怪物（均在中央牌列），获得3荣誉。",
    "Dreamseeker": "获得1洞察并抽一张牌。",
    "Dreamseeker Start": "获得1洞察并抽一张牌。",
    "Dreamwalker": "放逐中央牌列的一张卡牌。\n若被替换为怪物，获得2洞察。\n若被替换为英雄，获得2荣誉。\n若被替换为神器，抽两张牌。",
    "Emma's Mechannon": "每回合一次，你每控制一个已转化的机械神器，获得1战力。",
    "Emma's Teletransmitter": "每回合一次，你每控制一个已转化的机械神器，获得1荣誉。",
    "Emma's Voidcycler": "每回合一次，你每控制一个已转化的机械神器，获得1符文。",
    "Emma's Workshop": "每回合一次，你可以将一个机械神器转化且无需支付费用。",
    "Emri, Soulstealer": "获得5战力。若虚空区中有10个或更多怪物，改为获得10战力。",
    "Entrophantasm": "获得1符文和1洞察。\n联合：抽一张牌。（若你本回合打出或已打出过另一张命约英雄，则获得此效果。）",
    "Faerie Commander": "获得2符文。本回合你下次从中央牌列获取英雄时，获得2战力。",
    "Forgemother Reysa": "选择一项：抽一张牌；或获取中央牌列中任意数量的神器，无需支付费用。",
    "Gearseer": "幻象——当此牌在中央牌列时，你可以支付6洞察放逐并打出此牌。\n获得3符文。",
    "Giant Rat": "置于巨鼠之下的任何卡牌不能被获取、放逐或击败，直到巨鼠被放逐或击败。\n奖励：获得1荣誉。",
    "Green Spritelings": "幻象——当此牌在中央牌列时，你可以支付4洞察放逐并打出此牌。\n获得3荣誉。",
    "Hedron Rising": "所有神器也视为机械神器。\n事件战利品：当你控制的神器将被摧毁时，你可以防止其被摧毁。",
    "Invokist": "幻象——当此牌在中央牌列时，你可以支付4洞察放逐并打出此牌。\n获得3战力。",
    "Karion": "奖励：获得5荣誉和10洞察。",
    "Landis' Potions & Pies": "每回合一次，获得1荣誉。\n联合：获得1符文。",
    "Loa, Dream Dragon": "掷谵妄骰。",
    "Lychan Beast": "获得3符文和3战力。",
    "Mechannon Blueprint": "你可以支付5洞察，将此牌转化为艾玛的机加农。",
    "Moken, the Huntmaster": "获得5荣誉。\n游戏结束时，此牌的荣誉值等于你牌库中宝藏牌的数量。",
    "Moonveil Clique": "获得2符文。\n联合：回合结束时，将此牌置于你的手牌而非弃牌堆。",
    "Nightmarauders": "奖励：获得1荣誉和1洞察。",
    "Nilhammer": "回响：每回合一次，获得3战力。（若你的弃牌堆中有虚空卡牌，则获得此效果。）",
    "Nilia, The Shattered": "奖励：获得5荣誉。从一名对手的手牌中随机取一张牌加入你的手牌。\n梦缚：7洞察。",
    "Oak of Souls": "奖励：获得3荣誉。掷谵妄骰。",
    "Obfusca Spirit": "奖励：获得4荣誉。选择一名对手，令其从手牌中随机弃一张牌。\n梦缚：4洞察。",
    "P.R.I.M.E. Directive": "若你控制8个或更多机械神器，你赢得游戏。",
    "Polaris Demon": "奖励：5荣誉。选择一项：摧毁对手控制的所有偶数费用神器；或摧毁对手控制的所有奇数费用神器。",
    "Pollen Pixie": "获得2符文和1荣誉。",
    "Portal": "此牌可以是任意《创升纪元》系列中央牌库中可能出现的英雄或神器。你永远不知道会得到什么！",
    "Psyche Askara": "复制你本回合打出过的一张英雄的效果，或你本回合获得过的一个怪物奖励。",
    "Psyonic Paladin": "击败中央牌列中的一个怪物，无需支付费用。",
    "Rakar, Corrupt Askara": "奖励：获得6荣誉。将虚空区中的一张梦缚怪物加入你的手牌。",
    "Rat King": "当鼠王进入中央牌列时，在每个其他中央牌列空位上放置一张巨鼠。\n奖励：获得4荣誉，并击败场上所有巨鼠。",
    "Riftgate Conjuror": "获得3战力。\n本回合你下次击败虚空怪物时，额外再获得一次其奖励。",
    "Ring of Life": "每回合一次，若你本回合打出过命约英雄，获得1符文。当生命之环进入战场时，选择一个派系。你该派系的英雄也视为命约英雄。",
    "River Reaper": "奖励：获得6荣誉。每位对手摧毁其控制的神器，只保留一个。",
    "Salvage Yard": "在你的回合开始时，将此牌返回你的手牌。",
    "Scrapbot Scrapper": "获得2战力。你可以将你控制的一个神器返回手牌。",
    "Starlight Sanctum": "每回合一次，获得2符文。\n每回合一次，当你从中央牌列获取英雄时，你可以再获取一张费用等于或更低的英雄，无需支付费用。",
    "Teletransmitter Blueprint": "你可以支付5洞察，将此牌转化为艾玛的远传器。",
    "Terminites": "奖励：获得3荣誉。每位对手摧毁其控制的费用最低的神器。",
    "The Ironheart": "每回合一次，获得3符文、3战力和3荣誉。",
    "Torment Legionary": "奖励：获得6荣誉。获取中央牌列中的一张梦生卡牌，无需支付费用。",
    "Tree of Bounty": "掠夺——每回合一次，若你获取一张卡牌并且击败一个怪物（均在中央牌列），获得3荣誉。",
    "Tuskrider": "抽一张牌。\n联合：获得4战力。",
    "Vezra'Tull, The Voidwyrm": "你可以花费战力而非荣誉来获取此牌。\n虚空区中每有一个怪物，获得1战力。",
    "Void Mesmer": "获得2战力。本回合你下次击败怪物时，你可以获取一张费用等于或更低的英雄。",
    "Voidcycler Blueprint": "你可以支付5洞察，将此牌转化为艾玛的虚空循环器。",
    "Voidspeaker": "获得2战力。\n回响：获得3符文。（若你的弃牌堆中有虚空卡牌，则获得此效果。）",
    "Warpdruid": "奖励：获得2荣誉。你可以放逐你手牌或弃牌堆中的一张牌。\n梦缚：1洞察。",
    "Warprogue": "奖励：获得3荣誉。从一名对手处夺取1洞察。\n梦缚：3洞察。",
    "Wereboar": "获得2战力。\n联合：获得3符文。",
    "Zinta's Bracers": "每回合一次，若你已获得2点或更多洞察，获得2战力。",
    "Zis, Dreamreaper": "奖励：获得5荣誉。从每位对手处夺取2洞察。",
}


def _latin_ok(text: str) -> bool:
    for w in WORD.findall(text or ""):
        if w in ALLOW_LATIN or (w + ".") in ALLOW_LATIN:
            continue
        return False
    return True


def main() -> None:
    dirty_path = ROOT / "loc" / "inventory" / "phase2_dirty_ids.txt"
    dirty = [x for x in dirty_path.read_text(encoding="utf-8").splitlines() if x.strip()]

    with ZH_LUA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())
    by_id = {r["id"]: r for r in rows}

    applied = 0
    missing = []
    for cid in dirty:
        r = by_id.get(cid)
        if not r:
            missing.append(cid)
            continue
        if cid in EFFECTS:
            r["effect_text"] = EFFECTS[cid]
            applied += 1
        blob = "\n".join(
            [r.get("display_name") or "", r.get("effect_text") or "", r.get("flavor_text") or ""]
        )
        if _latin_ok(blob):
            r["source"] = "community"

    auto = 0
    for r in rows:
        if (r.get("source") or "") != "machine":
            continue
        blob = "\n".join(
            [r.get("display_name") or "", r.get("effect_text") or "", r.get("flavor_text") or ""]
        )
        if _latin_ok(blob):
            r["source"] = "community"
            auto += 1

    with ZH_LUA.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    left_machine = [r["id"] for r in rows if (r.get("source") or "") == "machine"]
    print(
        f"applied_hand={applied} auto_promote={auto} "
        f"machine_left={len(left_machine)} missing_map={sorted(set(dirty) - set(EFFECTS))}"
    )
    print("still_machine_sample", left_machine[:20])


if __name__ == "__main__":
    main()
