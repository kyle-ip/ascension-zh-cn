# -*- coding: utf-8 -*-
"""Rebuild polluted cards.csv FLAVOR_/EFFECT_ from EN sheets.

- FLAVOR: only FLAVOR_EXACT (no word-by-word). Unmatched → keep English source
  (clean EN beats mixed EN/ZH garbage).
- EFFECT: retranslate via translate_effect when mixed or empty.
- Also write achievements into ui_runtime.csv.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from translate import (  # noqa: E402
    FLAVOR_EXACT,
    strip_drop_cap,
    translate_effect,
    translate_flavor,
)

ZH_CARDS = ROOT / "loc" / "zh-Hans" / "cards.csv"
EN_SHEET = ROOT / "loc" / "en" / "sheets" / "Ascension_Cards.csv"
UI_RUNTIME = ROOT / "loc" / "zh-Hans" / "ui_runtime.csv"


def load_two_col(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or "," not in line:
            continue
        k, rest = line.split(",", 1)
        out[k.strip()] = rest.strip().strip('"').replace('""', '"')
    return out


def write_two_col(path: Path, data: dict[str, str]) -> None:
    lines = []
    for k, v in data.items():
        if any(ch in v for ch in ',"\n'):
            v = '"' + v.replace('"', '""') + '"'
        lines.append(f"{k},{v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def strip_markup(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\$\{[^}]+\}", " ", s)
    return s


def is_mixed(zh: str) -> bool:
    if not zh:
        return False
    plain = strip_markup(zh)
    return bool(re.search(r"[\u4e00-\u9fff]", plain)) and bool(
        re.search(r"[A-Za-z]{3,}", plain)
    )


def flavor_safe(en: str) -> str:
    """Prefer curated exact; never emit word-level garbage."""
    if not en or en.strip() in ('""', '"'):
        return ""
    plain = strip_drop_cap(en).strip().strip('"')
    collapsed = re.sub(r"\s+", " ", plain)
    if plain in FLAVOR_EXACT:
        return FLAVOR_EXACT[plain]
    for e, z in FLAVOR_EXACT.items():
        if re.sub(r"\s+", " ", e.strip().strip('"')) == collapsed:
            return z
    # curated translate_flavor only if result is clean CJK (no latin words)
    zh = translate_flavor(en)
    if zh and not is_mixed(zh) and re.search(r"[\u4e00-\u9fff]", zh):
        return zh
    # Fall back to English (clean) — LocPostfix/Exact can still improve later.
    return plain


# Extra high-visibility flavors (Arbiter etc.)
EXTRA_FLAVOR: dict[str, str] = {
    '"Memory and history are no concern of mine. This foul thing should never have existed.  Now, it will be as if it never did."':
        "「记忆与历史与我无关。这污秽之物本不该存在。如今，它将如同从未存在过。」",
    "Memory and history are no concern of mine. This foul thing should never have existed.  Now, it will be as if it never did.":
        "「记忆与历史与我无关。这污秽之物本不该存在。如今，它将如同从未存在过。」",
    "Find them standing on the edge of the abyss,<br>just beyond the jagged city.":
        "在锯齿般的城市之外，<br>它们立于深渊边缘。",
    "No matter how far he may wander, he can always find his way back to his mushroom.":
        "无论他游荡多远，总能找到回到蘑菇身边的路。",
}


def main() -> None:
    FLAVOR_EXACT.update(EXTRA_FLAVOR)

    zh = load_two_col(ZH_CARDS)
    en: dict[str, str] = {}
    with EN_SHEET.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            en[r["key"]] = r.get("en") or ""

    flav_fixed = eff_fixed = 0
    for key, ev in en.items():
        if key.startswith("FLAVOR_"):
            old = zh.get(key, "")
            new = flavor_safe(ev)
            # Always rewrite if mixed, empty-with-source, or differs from safe
            if is_mixed(old) or (not old and ev) or (new and new != old and not is_mixed(new)):
                if new != old:
                    zh[key] = new
                    flav_fixed += 1
        elif key.startswith("EFFECT_"):
            old = zh.get(key, "")
            if is_mixed(old) or not old:
                new = translate_effect(ev) if ev else old
                if new and new != old:
                    zh[key] = new
                    eff_fixed += 1

    # Also scrub any leftover mixed flavors whose EN key might be missing
    for key, old in list(zh.items()):
        if key.startswith("FLAVOR_") and is_mixed(old):
            ev = en.get(key, "")
            zh[key] = flavor_safe(ev) if ev else re.sub(r"[A-Za-z]{3,}", "", old)
            flav_fixed += 1

    write_two_col(ZH_CARDS, zh)
    print(f"cards.csv flavors fixed≈{flav_fixed} effects fixed≈{eff_fixed}")

    # --- achievements ---
    achievements = [
        ("Achievements", "成就"),
        ("On Your Way", "初出茅庐"),
        ("Win a game.", "赢得一局。"),
        ("Win a game", "赢得一局"),
        ("First Beat Down", "首次痛击"),
        ("First Beatdown", "首次痛击"),
        ("Win a game against another player", "对另一名玩家赢得一局"),
        ("Hot Streak", "连胜热潮"),
        ("Win 10 games in a row", "连续赢得 10 局"),
        ("The Benjamin", "本杰明"),
        ("Win 100 games", "赢得 100 局"),
        ("Treasure Trove", "金银满仓"),
        ("Acquire five or more treasure in the same turn", "同一回合获取五件或更多宝藏"),
        ("Clean Bill of Health", "健康证明"),
        ("Win a game with no Infest cards in your deck using Gift of the Elements",
         "使用《元素的馈赠》且牌组中无寄生牌的情况下赢得一局"),
        ("Energizer Bunny", "劲量兔"),
        ("Gain 10 energy in one turn", "一回合获得 10 点能量"),
        ("Yoink", "抢过来"),
        ("Defeat Xeron, Duke of Lies in a 4 player game", "在四人局中击败谎言之公爵塞伦"),
        ("Rally On", "集结起来"),
        ("Successfully rally one time with each faction", "每个派系成功集结一次"),
        ("Multi-United and it feels so good", "多重联合，感觉真好"),
        ("Multi-Unite the same card three times in a single turn", "同一回合对同一张牌多重联合三次"),
        ("Have Everything – CoG", "全集——弑神编年史"),
        ("Have Everything - CoG", "全集——弑神编年史"),
        ("Acquire or defeat every card in Chronicle of the Godslayer", "获取或击败《弑神编年史》中的每张牌"),
        ("Recruiter", "征募官"),
        ("Acquire 1000 center row Heroes", "获取 1000 张中央牌列英雄"),
        ("Greedy Treasure Hunter", "贪婪寻宝人"),
        ("Have Moken the Huntsmaster in your deck with at least 10 treasures",
         "牌组中有猎手莫肯且至少拥有 10 件宝藏"),
        ("Champion Of Champions", "冠军中的冠军"),
        ("Win a game with each of the Champions", "使用每位冠军各赢得一局"),
        ("Over 9000!!", "超过九千！！"),
        ("Gain 9001 honor points", "获得 9001 点荣誉"),
        ("Freebee", "白嫖"),
        ("Acquire Oziah for free with Energy", "用能量免费获取奥齐亚"),
        ("Cult Killer", "邪教杀手"),
        ("Kill the Cultist 1000 times", "击杀邪教徒 1000 次"),
        ("Soul Fire", "灵魂之火"),
        ("Play 5 Soul Gems in 1 turn", "一回合打出 5 枚灵魂宝石"),
        ("Lucky Godslayer", "幸运的弑神者"),
        ("Acquire Hedron Cannon after defeating Avatar of the Fallen that turn",
         "在击败堕天化身的同一回合获取多面体加农炮"),
        ("Living The Dream", "活在梦里"),
        ("Acquire two Dream Vision cards without paying their cost during a single game",
         "单局内免费获取两张梦境幻象牌"),
        ("Monsters? You Don't Need No Stinkin' Monsters", "怪物？才不需要那些臭怪物"),
        ("Gain more than 20 Honor by playing a single card", "打出单张牌获得超过 20 荣誉"),
        ("Born Again", "重生"),
        ("Acquire all Dreamborn cards in Dreamscape", "获取梦境中所有梦生牌"),
        ("All Day, All Night", "整日整夜"),
        ("Gain a DAY bonus and a NIGHT bonus in the same turn", "同一回合获得日间与夜间加成"),
        ("Vanquisher", "征服者"),
        ("Defeat 1000 center row Monsters", "击败 1000 个中央牌列怪物"),
        ("Soul Collector", "灵魂收集者"),
        ("Use each of the Soul Gems", "使用每一种灵魂宝石"),
        ("Serenity Now", "立刻平静"),
        ("Multi-Unite Adayu the Serene with at least one card from each faction on a single turn",
         "同一回合以多重联合打出宁静阿达尤，且包含每个派系至少一张牌"),
        ("Pasythea Go", "帕茜西亚出发"),
        ("Acquire Pasythea, the Aegis using Pasythea's Ward", "用帕茜西亚的守护获取神盾帕茜西亚"),
        ("Livin' on the Edge", "刀锋边缘"),
        ("Have Umbral edge and Penumbral Edge in play at the same time", "同时在场拥有暗影刃与半影刃"),
        ("Don't Feed Them After Midnight", "午夜后别喂它们"),
        ("Infest your opponent's deck with all of the Bam, Yuk, and Nom Tribe Gremlins",
         "用全部砰、恶、啃部落的哥布林寄生对手牌组"),
        ("Don't mind if Adayu", "阿达尤不介意"),
        ("Defeat Samael the Fallen with Adayu", "用阿达尤击败堕天萨麦尔"),
        ("Tag Team", "双打"),
        ("Take an extra turn with Wandering Askara", "用流浪阿斯卡拉获得额外回合"),
        ("Herald of Winning", "胜利先驱"),
        ("Defeat and Energize Herald of Doom", "击败并充能末日先驱"),
        ("Yolo Twice", "再浪一次"),
        ("Return Yolocryx from the discard pile to your hand", "将尤洛克瑞克斯从弃牌堆返回手牌"),
        ("Builder", "建造者"),
        ("Play 1000 Constructs", "打出 1000 张神器"),
        ("Deal With It", "认了吧"),
        ("Roll the Delirium Die using the Dream Dealer's effect.", "用梦境发牌人的效果掷谵妄骰。"),
        ("Roll the Delirium Die using the Dream Dealer's effect", "用梦境发牌人的效果掷谵妄骰"),
        ("Assassin", "刺客"),
        ("Win 10 games in a row against other players", "对其他玩家连续赢得 10 局"),
        ("P.R.I.M.E.'d for Victory", "P.R.I.M.E. 制胜"),
        ("Win a game as a result of P.R.I.M.E. Directive", "因 P.R.I.M.E. 指令赢得一局"),
        ("Hunting Party", "狩猎小队"),
        ("Play Flare Tracker and Sureshot Tracker in the same turn", "同一回合打出闪光追踪者与必中追踪者"),
        ("More than meets the Eye", "不止所见"),
        ("Transform all of the cards in Darkness Unleashed", "转化《暗影之战》中的所有可转化牌"),
        ("Serenity Now Now Now Now...", "立刻立刻立刻平静……"),
        ("Trigger both Serenity and Echo on the same turn.", "同一回合触发宁静与回响。"),
        ("Trigger both Serenity and Echo on the same turn", "同一回合触发宁静与回响"),
        ("Have Everything – RotF", "全集——堕天归来"),
        ("Have Everything - RotF", "全集——堕天归来"),
        ("Acquire or defeat every card in Return of the Fallen", "获取或击败《堕天归来》中的每张牌"),
        ("Have Everything – SoS", "全集——灵魂风暴"),
        ("Have Everything - SoS", "全集——灵魂风暴"),
        ("Acquire or defeat every card in Storm of Souls", "获取或击败《灵魂风暴》中的每张牌"),
        ("Weapon X", "武器 X"),
        ("Have at least one of each Mechana construct from Chronicle of the Godslayer in play at the same time",
         "同时在场拥有《弑神编年史》中每一种机械神器至少一张"),
        ("Cobra King Midas", "眼镜蛇王迈达斯"),
        ("Gain 20 Honor in a single turn with Jakeb, Cobra King", "用眼镜蛇王杰克布单回合获得 20 荣誉"),
        ("You must be Aaron", "你一定是亚伦"),
        ("Defeat Avatar of the Fallen and Samael the Fallen in the same turn",
         "同一回合击败堕天化身与堕天萨麦尔"),
        ("Dream Big", "敢于梦想"),
        ("Acquire Dream Machine with P.R.I.M.E.", "用 P.R.I.M.E. 获取梦境机器"),
        ("Dream On", "继续做梦"),
        ("Acquire all Vision cards in Dreamscape", "获取梦境中所有幻象牌"),
        ("Beastly Staff", "野兽之杖"),
        ("Gain 5 Honor or more from the reveal of Beast Staff", "从揭示野兽之杖获得 5 点或更多荣誉"),
        ("Devil's Triangle", "魔鬼三角"),
        ("Roll three 6s on the Delirium Die in a single game.", "单局在谵妄骰上掷出三次 6。"),
        ("Roll three 6s on the Delirium Die in a single game", "单局在谵妄骰上掷出三次 6"),
        ("BF Sword", "大剑"),
        ("Defeat five monsters in a single turn with Oziah", "用奥齐亚单回合击败五个怪物"),
        ("God Of Plunder", "掠夺之神"),
        ("Activate the Plunder effect five times in a single game.", "单局发动掠夺效果五次。"),
        ("Activate the Plunder effect five times in a single game", "单局发动掠夺效果五次"),
        ("Glutton For Punishment", "自讨苦吃"),
        ("Defeat Aranyx, the Glutton and Xeron, Lord of Deofol on the same turn",
         "同一回合击败贪食者阿兰克斯与德俄佛之主塞伦"),
        ("Draaaaaaaw!", "抽——牌！"),
        ("Using Dhartha, Mechamonk, draw seven or more cards in a single turn.",
         "用机械僧达尔塔单回合抽七张或更多牌。"),
        ("Using Dhartha, Mechamonk, draw seven or more cards in a single turn",
         "用机械僧达尔塔单回合抽七张或更多牌"),
        ("Cult Friendly", "邪教友善"),
        ("Win 10 games without killing the Cultist", "不击杀邪教徒的情况下赢得 10 局"),
        ("Canon Cannon", "加农圣炮"),
        ("Defeat Adayu the Tormented using Canon Templar", "用加农圣堂武士击败受折磨的阿达尤"),
        ("Follow The Leader", "跟着领袖"),
        ("Aquire 7 Heroes in a single turn while playing with only Realms Unraveled",
         "仅使用《领域解开》时单回合获取 7 名英雄"),
        ("Acquire 7 Heroes in a single turn while playing with only Realms Unraveled",
         "仅使用《领域解开》时单回合获取 7 名英雄"),
        ("Going Once, Going Twice...", "一次出价，两次出价……"),
        ("Win two Fate Auctions on a single turn.", "同一回合赢得两次天命拍卖。"),
        ("Win two Fate Auctions on a single turn", "同一回合赢得两次天命拍卖"),
        ("The Fifth Elements", "第五元素"),
        ("Acquire all five of the Transformed Events/Heroes across multiple games",
         "跨越多局获取全部五张转化后的事件/英雄"),
        ("Ouch That Stings", "好痛"),
        ("Defeat a Monster in the Center Row with Emri's Sting and Emri, Demonsbane",
         "用艾姆瑞之刺与屠魔者艾姆瑞击败中央牌列怪物"),
        ("United We Stand", "联合则立"),
        ("Play 5 Lifebound heroes in a single turn while playing with only Storm of Souls",
         "仅使用《灵魂风暴》时单回合打出 5 名命约英雄"),
        ("Catch 'em all", "全都要"),
        ("Defeat all 5 Growmites in the same game", "同一局击败全部 5 只增生螨"),
        ("Piper at the Gates of Dawn", "黎明门前的吹笛人"),
        ("Win a game where the only cards you've acquired are Day cards", "仅获取日间牌的情况下赢得一局"),
        ("Night Owl", "夜猫子"),
        ("Win a game where the only cards you've acquired are Night cards", "仅获取夜间牌的情况下赢得一局"),
        ("A Complete Transformation", "完全转化"),
        ("Transform all of the cards in Deliverance.", "转化《拯救》中的所有可转化牌。"),
        ("Transform all of the cards in Deliverance", "转化《拯救》中的所有可转化牌"),
        ("Trophy Room", "战利品室"),
        ("Have one of each trophy monster in play at the same time while playing with Storm of Souls",
         "使用《灵魂风暴》时同时在场拥有每种战利品怪物各一"),
        ("Boon Balloon", "恩赐气球"),
        ("Use a Boon from every faction in one turn.", "一回合使用每个派系的恩赐。"),
        ("Use a Boon from every faction in one turn", "一回合使用每个派系的恩赐"),
        ("Master Assassin", "刺客大师"),
        ("Play Deadeye Assassin with 10 or more Void cards in your discard pile",
         "弃牌堆有 10 张或更多虚空牌时打出神射手刺客"),
        ("Deja Vu", "似曾相识"),
        ("Use the Recur effect found on all cards with a Recur effect in Delirium.",
         "使用《谵妄》中所有带循环效果之牌的循环效果。"),
        ("Use the Recur effect found on all cards with a Recur effect in Delirium",
         "使用《谵妄》中所有带循环效果之牌的循环效果"),
        ("Monster Mash", "怪物狂欢"),
        ("Have one of each Return of the Fallen Monster in your deck while Samael is in play",
         "萨麦尔在场时牌组中拥有《堕天归来》每种怪物各一"),
        ("Wicked Game", "邪恶游戏"),
        ("Use Wicked End to defeat Ender of Days", "用邪恶终焉击败末日终结者"),
        ("Time Machine", "时间机器"),
        ("Take 5 turns in a row while playing with Return of the Fallen", "使用《堕天归来》时连续进行 5 个回合"),
        ("Stay Focused", "保持专注"),
        ("Win a game with only two factions in your deck while playing with only Realms Unraveled",
         "仅使用《领域解开》且牌组只有两个派系时赢得一局"),
        ("Three Cannon Salute", "三炮敬礼"),
        ("Play Hedron Cannon, Plasma Cannon, and Canon Templar on the same turn",
         "同一回合打出多面体加农炮、等离子加农炮与加农圣堂武士"),
        ("Soul Sisters", "灵魂姐妹"),
        ('Play "Naka, Emri\'s Chosen" and "Emri, Soulstealer" on the same turn.',
         "同一回合打出「艾姆瑞选民娜卡」与「窃魂者艾姆瑞」。"),
        ('Play "Naka, Emri\'s Chosen" and "Emri, Soulstealer" on the same turn',
         "同一回合打出「艾姆瑞选民娜卡」与「窃魂者艾姆瑞」"),
        ("The Tall Man Approves", "高个子批准了"),
        ("Activate the Phantasm effect five times in a single game.", "单局发动幻影效果五次。"),
        ("Activate the Phantasm effect five times in a single game", "单局发动幻影效果五次"),
        ("Time Traveler", "时间旅行者"),
        ("Take 5 turns in a row while playing with only Chronicle of the Godslayer",
         "仅使用《弑神编年史》时连续进行 5 个回合"),
        ("Whoa. Whoa. Whoa. What are you doing?", "喂。喂。喂。你在干什么？"),
        ("Take all three Temples from your opponent(s) on the final turn of the game and win.",
         "在终局回合夺走对手全部三座神庙并获胜。"),
        ("Take all three Temples from your opponent(s) on the final turn of the game and win",
         "在终局回合夺走对手全部三座神庙并获胜"),
        ("A Legend Among Legends", "传奇中的传奇"),
        ("Reach Legendary Status with all Legendary Characters.", "使所有传奇角色达到传奇地位。"),
        ("Reach Legendary Status with all Legendary Characters", "使所有传奇角色达到传奇地位"),
        ("I Guess It Just Froze Over", "看来这里结冰了"),
        ("Defeat five Hellfrost Imps on a single turn.", "单回合击败五只狱霜小鬼。"),
        ("Defeat five Hellfrost Imps on a single turn", "单回合击败五只狱霜小鬼"),
        ("Jubilee!", "欢庆！"),
        ("Using only Valley of the Ancients, draw your entire deck using Jubilant Monk.",
         "仅使用《上古山谷》，用欢庆僧侣抽完整个牌库。"),
        ("Using only Valley of the Ancients, draw your entire deck using Jubilant Monk",
         "仅使用《上古山谷》，用欢庆僧侣抽完整个牌库"),
        ("Ascension: A Deck Empowering Game", "创升纪元：赋能构筑"),
        ("Win a game with 5 or fewer cards in your deck", "牌组不超过 5 张时赢得一局"),
        ("Four Of Swords", "四剑"),
        ("Acquire Pasythea, The Redeemed for free.", "免费获取救赎者帕茜西亚。"),
        ("Acquire Pasythea, The Redeemed for free", "免费获取救赎者帕茜西亚"),
        ("Shackled", "被缚"),
        ("Using only Deliveraance, finish a game with only Dreambind cards in your deck.",
         "仅使用《拯救》，以牌组全为梦缚牌结束一局。"),
        ("Using only Deliverance, finish a game with only Dreambind cards in your deck.",
         "仅使用《拯救》，以牌组全为梦缚牌结束一局。"),
        ("Using only Deliverance, finish a game with only Dreambind cards in your deck",
         "仅使用《拯救》，以牌组全为梦缚牌结束一局"),
        ("Messenger Mandate", "信使使命"),
        ("Win the game with the effect of Ahra Emissary.", "用阿哈特使的效果赢得游戏。"),
        ("Win the game with the effect of Ahra Emissary", "用阿哈特使的效果赢得游戏"),
        ("Monkopoly", "僧侣垄断"),
        ("Play Dark Monk, Psionic Monk, and Monk of the Stone Circle in the same turn.",
         "同一回合打出暗僧、灵能僧与石环僧侣。"),
        ("Play Dark Monk, Psionic Monk, and Monk of the Stone Circle in the same turn",
         "同一回合打出暗僧、灵能僧与石环僧侣"),
        ("Thrice Reborn", "三次重生"),
        ("Play Mechaphoenix three times in one turn.", "一回合打出机械凤凰三次。"),
        ("Play Mechaphoenix three times in one turn", "一回合打出机械凤凰三次"),
        # card type lines common in gallery
        ("Event - Monster", "事件 - 怪物"),
        ("Event - Hero", "事件 - 英雄"),
        ("Hero - Monster", "英雄 - 怪物"),
        ("Gain 1 Honor instead.", "改为获得 1 荣誉。"),
        ("Gain 2 Honor instead.", "改为获得 2 荣誉。"),
        ("Gain 3 Honor instead.", "改为获得 3 荣誉。"),
        ("Gain Honor instead.", "改为获得荣誉。"),
        ("Gain ★ instead.", "改为获得★。"),
        ("Gain <sprite=0> instead.", "改为获得<sprite=0>。"),
    ]

    rows: list[dict[str, str]] = []
    if UI_RUNTIME.is_file():
        with UI_RUNTIME.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    existing = {(r.get("en") or "").strip() for r in rows}
    added = 0
    for en_s, zh_s in achievements:
        if en_s.strip() in existing:
            # update zh if was missing/english
            for r in rows:
                if (r.get("en") or "").strip() == en_s.strip():
                    if (r.get("zh") or "").strip() in ("", en_s.strip()):
                        r["zh"] = zh_s
                        added += 1
            continue
        rows.append({"en": en_s, "zh": zh_s})
        existing.add(en_s.strip())
        added += 1
    with UI_RUNTIME.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["en", "zh"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"ui_runtime achievements/type lines upserted≈{added} total={len(rows)}")


if __name__ == "__main__":
    main()
