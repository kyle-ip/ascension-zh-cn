# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH_LUA = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
UI_RT = ROOT / "loc" / "zh-Hans" / "ui_runtime.csv"
WORD = re.compile(r"[A-Za-z]{3,}")

FLAVORS = {
    "Dreamscape Diviner": "你确定想知道吗？",
    "Loa, Dream Dragon": "他的灵魂，借梦境显现。",
    "Dream Stone": "凝视那本可能发生、以及即将到来之事。",
    "Pollen Pixie": "一开始你会觉得有点晕……",
    "Dream Guide": "在世界的边缘，她是通往一切未知的向导。",
    "Tuskrider": "松露与人肉。",
    "Scrapbot Scrapper": "某人之废，恰为机兵之器。",
    "Voidspeaker": "对人类情感有着贪婪的胃口。",
    "Darktome Librarian": "小心，第六页会咬人。",
    "Arbiter Circlet": "恶魔之骨，以及一百个灵魂。",
    "Nilhammer": "需要能敲碎骨头与心魄的东西吗？",
    "Demon Pups": "我只是想摸摸它！",
    "Dream Eater": "梦境痛苦，现实更是折磨。",
    "Delirium Pixies": "来和我们一起玩吧。",
    "Dreadmare": "日啖一魂，惧马远离。",
    "Oak of Souls": "意识之死，发生于无意识的世界。",
    "Zis, Dreamreaper": "死法有多少种，梦就有多少场。",
    "Torment Legionary": "无尽的野心，超越死亡，超越现实。",
    "Karion": "梦境之门已然腐化，是横跨两界的炼狱伤口。",
    "Dreamseeker Start": "梦造就人，亦摧毁人。",
    "Dreamwalker": "你确定想知道吗？",
    "Dream Chamber Disciples": "亚哈教导我们：一切传统终将被原则的重量压垮。",
    "Psyonic Paladin": "盔甲由我们的意念塑形，剑锋由我们的意志指引。",
    "Aether Warrior": "我的刃斩断血肉，亦斩断灵魂。",
    "Psyche Askara": "亚哈教导我们：一切传统终将被原则的重量压垮。",
    "Entrophantasm": "你确定想知道吗？",
    "Dreamscarred Hunter": "你确定想知道吗？",
    "Faerie Commander": "他在森林里被发现时，身上已有百万道细伤。",
    "Green Spritelings": "你确定想知道吗？",
    "Wereboar": "你确定想知道吗？",
    "Lychan Beast": "他们永远看不到我靠近。",
    "Tree of Bounty": "你确定想知道吗？",
    "Gearseer": "天才与疯狂的唯一差别，在于能否做成。",
    "Teletransmitter Blueprint": "像心灵感应，但没那么好用。\n——艾玛·铁心",
    "Emma's Teletransmitter": "「我要是不需要帮忙，干嘛还打给你？」——艾玛·铁心",
    "Mechannon Blueprint": "「不知道这玩意儿能砸出多大坑。」——艾玛·铁心",
    "Emma's Mechannon": "「看到了吗？我在那座山上打了个洞！」——艾玛·铁心",
    "Voidcycler Blueprint": "「不知道这玩意儿能砸出多大坑。」——艾玛·铁心",
    "Emma's Voidcycler": "「这证明了，艾玛，你是个天才。」——艾玛·铁心",
    "Emma's Workshop": "「这地方快散架了。完美。」——艾玛·铁心",
    "The Ironheart": "「管你有多少触手。我可是有飞艇！」——艾玛·铁心",
    "Demon Hunter": "好人也罢，坏人也罢。试试带剑的那个。",
    "Demon Master": "工作艰难，气味更糟。",
    "Invokist": "恐惧也有面孔。\n让我指给你看。",
    "Nihil Bomber": "恐惧也有面孔。",
    "Emri, Soulstealer": "又是一天，又收割一位半神。",
    "Zinta's Bracers": "辛塔伸手探入虚空，从中抽出双匕。",
    "Nightmarauders": "他们无处不在！",
    "Terminites": "不过是虫子罢了，士兵。能有多大？",
    "Warpdruid": "树皮裂开，血肉绽放。",
    "Warprogue": "爱是一场梦。爱是一场噩梦。",
    "Dream Titan": "黄金巨人，高过群山，静如大海。",
    "Obfusca Spirit": "爱是一场梦。爱是一场噩梦。",
    "Dream Tyrant": "黄金巨人，高过群山。",
    "River Reaper": "黄金巨人，高过群山。",
    "Caaro, Desert Breaker": "黄金巨人，高过群山。",
    "Nilia, The Shattered": "黄金巨人，高过群山。",
    "Rakar, Corrupt Askara": "爱是一场梦。爱是一场噩梦。",
    "Vezra'Tull, The Voidwyrm": "有的龙囤积黄金。她囤积噩梦。",
    "Landis' Potions & Pies": "你确定想知道吗？",
}


def main() -> None:
    with ZH_LUA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())
    applied = missing = 0
    for r in rows:
        if r["id"] in FLAVORS:
            r["flavor_text"] = FLAVORS[r["id"]]
            applied += 1
        elif WORD.search(r.get("flavor_text") or ""):
            missing += 1
            print("UNMAPPED", r["id"])
    with ZH_LUA.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"applied={applied} unmapped_latin={missing}")

    # UI runtime leftover cleanup by substring
    fixes = [
        ("EFFECT\nWhat", "效果\n此牌打出或在场上时的作用。"),
        ("COST\nThe amount", "费用\n获取此牌所需花费的战力。"),
        ("REWARD\nWhat this", "奖励\n击败此怪物时获得的效果。"),
        ("FLAVOR TEXT\n", "风味文本\n风味文本不影响规则。"),
        ("HONOR\nHow much", "荣誉\n此牌可提供多少荣誉。"),
        ("This is the flavor", "此处为风味文本。"),
        ("Press the avatar", "点击头像，从好友列表邀请好友。"),
        ("support@playdekgames.com", None),  # keep existing zh if already good
        ("FACTION\nThere are 4", "派系\n共有四大派系：\n<color=#4cbbeb>圣贤\n<color=#7fc241>命约\n<color=#b6b6b6>机械\n<color=#bb8bbe>虚空"),
        ("To defeat a Monster, you must have enough Power", "<margin-right=8em>要击败怪物，你必须拥有足够的战力。只要战力足够，你可以击败任意数量的怪物。</margin-right>"),
        ("If you previously had a Playdek account", "若你此前已有 Playdek 账号，或在我们其他游戏中使用过该账号，可用同一邮箱与密码登录。"),
        ("Purchase all the Ascension bundles", "一次购入全部《创升纪元》捆绑包，超值优惠！<br><br>包含捆绑包 #1 至 #5。<br><br>共计 630 张<b>独特</b>新卡可供游玩。"),
        ("A remnant of something long since forgotten", "被遗忘之物的残响，它们在祈夜的现身笼罩着谜团。"),
        ("Sharpen the mind", "磨砺心智，剑锋自至。"),
    ]
    with UI_RT.open(encoding="utf-8", newline="") as f:
        ui = list(csv.DictReader(f))
        ufields = list(ui[0].keys())
    n = 0
    for r in ui:
        en = r.get("en") or ""
        for needle, zh in fixes:
            if needle in en and zh is not None:
                r["zh"] = zh
                n += 1
                break
    with UI_RT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ufields, lineterminator="\n")
        w.writeheader()
        w.writerows(ui)
    print(f"ui_fixed={n}")


if __name__ == "__main__":
    main()
