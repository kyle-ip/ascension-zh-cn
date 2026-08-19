"""Build loc/zh-Hans/rulebook.csv from extracted English + glossary + card names."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from translate import (  # noqa: E402
    strip_drop_cap,
    translate_effect,
    translate_flavor,
    translate_label,
)
from rulebook_leftover_zh import ZH as LEFTOVER_ZH  # noqa: E402

EN_RB = ROOT / "loc" / "en" / "rulebook.csv"
OUT = ROOT / "loc" / "zh-Hans" / "rulebook.csv"
GLOSSARY = ROOT / "glossary" / "zh-Hans.csv"
ZH_LUA = ROOT / "loc" / "zh-Hans" / "lua_cards.csv"
EN_LUA = ROOT / "loc" / "en" / "lua_cards.csv"
ZH_CARDS = ROOT / "loc" / "zh-Hans" / "cards.csv"
EN_SHEET = ROOT / "loc" / "en" / "sheets" / "Ascension_Cards.csv"

SKIP = {"ystic", "ultist"}

# Manual rulebook copy. Keys are normalized English (\\n, stripped).
EXACT: dict[str, str] = {}


def n(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_glossary() -> dict[str, str]:
    out: dict[str, str] = {}
    factions: dict[str, str] = {}
    types: dict[str, str] = {}
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            en = (row.get("en") or "").strip()
            zh = (row.get("zh") or "").strip()
            if not en or not zh or en.startswith("#"):
                continue
            out[en] = zh
            out[en.lower()] = zh
            scope = (row.get("scope") or "").strip()
            if scope == "faction":
                factions[en] = zh
            elif scope == "type":
                types[en] = zh
    for fen, fzh in factions.items():
        for ten, tzh in types.items():
            out[f"{fen} {ten}"] = fzh + tzh
            out[f"{fen} {ten}s"] = fzh + tzh
            out[f"{fen.lower()} {ten.lower()}"] = fzh + tzh
    return out


def load_card_names() -> dict[str, str]:
    names: dict[str, str] = {}
    en_by_id: dict[str, str] = {}
    if EN_LUA.is_file():
        with EN_LUA.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                i = row.get("id") or row.get("card_name") or ""
                en_by_id[i] = row.get("display_name") or i
    if ZH_LUA.is_file():
        with ZH_LUA.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                i = row.get("id") or ""
                zh = row.get("display_name") or ""
                en = en_by_id.get(i, i)
                if en and zh:
                    names[n(en)] = zh
                    names[en.lower()] = zh
    en_sheet: dict[str, str] = {}
    if EN_SHEET.is_file():
        with EN_SHEET.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].startswith("CARDNAME_"):
                    en_sheet[row[0]] = row[1]
    if ZH_CARDS.is_file():
        with ZH_CARDS.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].startswith("CARDNAME_"):
                    en = strip_drop_cap(en_sheet.get(row[0], ""))
                    if en:
                        names[n(en)] = row[1]
    return names


def fill_exact() -> None:
    EXACT.update(
        {
            n(
                """When the worlds were born, there were five gods, each endowed with a unique spark of creation. After they created Vigil, they squabbled over how to rule it, eventually retreating to realms of their  own design.  Centuries turned into millenia, and the gods were content with their realms and followers. All except one.

The Fallen God Samael's insatiable hunger led him and his plane of Deofol on a dark quest that would unite the realms against him.  After countless wars, he met his end at the hands of other gods and their allies.

Samael's death threw the universe into disarray, as dark forces sought to ascend Deofol's throne, thinking that it would lead to their own ascent to godhood.  One by one, the realms defeated the would-be conquerors, but the universe's need for a balanced pantheon could not be ignored.

What was once thought to be the result of centuries of struggle and conflict, Adayu's Unraveling was not the result of madness.  It was the inception of a new divine spark, awakening Adayu to a new destiny that awaits him.

The awakening of a new god unleashed a wave of energy across the realms, sending them colliding into each other to form a new unified world of New Vigil.  The factions have adapted well to the new world, learning to work together and develop new technologies that utilize their combined strengths.

The four factions' realms weren't the only ones to be merged into New Vigil.  Deofol has been woven into the new realm as well, corrupting heroes and twisting them into a dark army to serve the Cult's new leader, a shadowy figure from Vigil's past.

Hoping to avoid repeating history, Adayu and the other gods have retreated beyond New Vigil, leaving mortals to guide their own destiny.  One to be determined not by Gods, but by Champions."""
            ): """世界诞生之时，有五位神明，各自秉持独特的创世火花。他们造就祈夜之后，为如何统治此界争执不休，最终退入各自设计的位面。世纪化为千年，诸神安于自己的疆域与信徒。唯有一位例外。

堕落之神萨麦尔永不餍足的饥渴，驱使他与其位面迪奥弗踏上黑暗征途，迫使诸界联合对抗。历经无数战争，他终于死在其他神明及其盟友手中。

萨麦尔之死令宇宙失序。黑暗势力争相登上迪奥弗的王座，以为如此便能自己登神。诸界一一击溃这些妄图征服者，但宇宙仍需要平衡的神谱，此事无法忽视。

曾被认作数百年争斗的结果——阿达尤的领域解开——并非疯狂所致。那是新神火的萌发，唤醒阿达尤去迎接等待着他的新命运。

新神觉醒释放出横扫诸界的能量波，使各界相互碰撞，融成统一的新世界：新祈夜。各派系很快适应新世界，学会合作，并发展出融合彼此长处的新技术。

并入新祈夜的不只是四派的疆域。迪奥弗也被织入新界，腐化英雄、将其扭曲成黑暗大军，听命于教团的新领袖——一个来自祈夜往昔的阴影人物。

为免重蹈覆辙，阿达尤与其他神明退到新祈夜之外，将命运交给凡人自己引导。那命运不再由神明决定，而由冠军决定。""",
            n(
                """It has been years since Kythis was defeated.  The Well of Souls once more welcomes home the long-suffering spirits of the fallen.  For the first time in generations, peace and prosperity replaced the chaos of bloody war.  From the seeds of death sprung hope as the people of Vigil rebuilt her war-torn cities and honored the sacrifices of her dead.

It was in this time of plenty that the mysterious shards appeared.  Like the crystalline tears of some weeping god, they rained upon Vigil in storms of pulsing light.  They were found casting their peculiar glow in long forgotten mines, abandoned temples, and silent shrines.  All the while, strange tales of enhanced sorcery, strength, and power spread.  Mystics and other arcane practitioners praised the gods for their divine gift, claiming the shards a reward for their many trials and tribulations.  Still others called for further study, cautioning all who would listen that such power never comes without a price.

And while the people of Vigil celebrate their new source of power, tales of twisted beasts and nightmarish creatures are told in whispers.  Vigil's hard won peace is poised to shatter, as strange new monsters defile once sacred sites and stalk the trails between the villages.  The power of the shards brought about the Rise of Vigil - will it now cause her fall?"""
            ): """凯西斯被击败已有数年。灵魂之井再次迎接饱经苦难的亡者之灵归乡。世代以来第一次，和平与繁荣取代了血战的混乱。死亡的种子里抽出希望：祈夜的人民重建饱受战火的城市，并纪念死者的牺牲。

正是在这丰饶之时，神秘碎片出现了。它们如同某位泣神的晶泪，在搏动的光雨中落向祈夜。人们在久被遗忘的矿坑、废弃神殿与寂静神龛中发现它们独特的辉光。与此同时，关于增强巫术、力量与战力的奇闻流传开来。秘教士和其他奥术修行者赞美神明的恩赐，称碎片是对他们诸多试炼的奖赏。也有人呼吁进一步研究，警告所有愿意倾听的人：如此力量从无免费。

当祈夜人民庆祝这新的力量之源时，关于扭曲野兽与梦魇生物的故事却在耳语中流传。祈夜来之不易的和平濒临破碎：陌生的新怪物玷污曾经神圣之地，出没于村落之间的小径。碎片的力量带来了祈夜崛起——如今，它会不会也导致她的陨落？""",
            n(
                """The game ends when a certain amount of Honor has been earned, depending on the number of players.

<align=center>
2 Players = <sprite=77> Honor   3 Players = <sprite=78> Honor   4 Players = <sprite=79> Honor<br></align><br>When the final Honor point is earned, the game ends at the end of the current round (after the last player to start the game takes a turn).  Thus, each player will play the same number of turns during the course of the game and may still gain Honor even when the Honor pool is depleted.<br><br>

Cards in each player's deck are also worth Honor points, indicated by the number in the Honor symbol (<sprite=64>) in the bottom left corner of each card.  When the game is over, all Honor points from Heroes and Constructs in your deck and hand are added to the Honor you gained during the game.  The player with the most total Honor is the winner!<br><br>If multiple players have the same number of Honor Points, the last player to start wins (i.e., the starting player loses all ties, the second player loses to the third and fouth, etc.).<br><br>"""
            ): """游戏在获得一定数量的荣誉后结束，所需数量取决于玩家人数。

<align=center>
2人 = <sprite=77> 荣誉   3人 = <sprite=78> 荣誉   4人 = <sprite=79> 荣誉<br></align><br>当最后一点荣誉被获得时，游戏在本轮结束时结束（在开局顺序最后的玩家完成其回合之后）。因此，整局中每位玩家的回合数相同；即使荣誉池已空，仍可继续获得荣誉。<br><br>

每位玩家牌库中的卡牌也计荣誉点数，见卡牌左下角荣誉符号（<sprite=64>）中的数字。游戏结束时，将你牌库与手牌中英雄和神器的荣誉，加到对局中已获得的荣誉上。总荣誉最高的玩家获胜！<br><br>若多名玩家荣誉点数相同，开局顺序最靠后的玩家获胜（即起始玩家在所有平局中落败，第二玩家输给第三、第四玩家，以此类推）。<br><br>""",
            n(
                """An era of unprecedented peace and prosperity seemed like a just reward for the weary denizens of New Vigil, but a world dominated by light is an imbalanced one. A new darkness seeps in from the Void, intent on restoring balance by restoring despair and desolation to a world that had forgotten it.

Aklys, the Scourge, leads his dark legion into New Vigil, determined to carve out a new kingdom of his own in New Vigils' growing shadows. They rise from the shadows and the dark corners, striking out at content and unprepared cities.

The four factions now recall their veteran heroes and reawaken the great war machines of the past, as they plan their first move in the chaotic ebb and flow of light and dark. Do they have what it takes to defeat Aklys and restore the balance between Night and Day, or will they fall victim to the fear and paranoia as the shadows themselves rise up against them? The War of Shadows has begun."""
            ): """前所未有的和平与繁荣，仿佛是对新祈夜疲惫居民的公正奖赏——但一个被光主宰的世界并不平衡。新的黑暗从虚空区渗入，意图把被遗忘的绝望与荒芜带回此界，以恢复平衡。

天灾阿克里斯率领黑暗军团杀入新祈夜，决心在新祈夜渐长的阴影中为自己开辟新王国。他们自阴影与暗角升起，突袭安逸而无防备的城市。

四派系召回老兵英雄，唤醒往昔的战争巨械，筹划在光暗混乱涨落中的第一步。他们能否击败阿克里斯、恢复夜与昼的平衡，还是会在阴影自身起身相向时，沦为恐惧与猜疑的牺牲品？暗影之战已经开始。""",
            n(
                """The shadow of Deofol still looms over Vigil. Samael has fallen, but his actions have forever scarred the foundation of the realms. His surviving minions are scattered and hidden, plotting evil. Yet, even as the Vigil gathers itself against this remaining enemy, it is beset by a new darkness. Specters now haunt the people of the land, their arrival hinting at a greater threat.

The visitors from Arha say that the afterlife itself is in turmoil. Gatekeeper Kythis, who since Time's Dawn had admitted the damned to their final resting place, stands watch no more. Now, a restless and tormented mass of wills churns beneath all existence, welling up between the worlds.

Where is the Gatekeeper? It was Samael that freed Kythis of his duty. Now he is missing, a rebel godling hidden even from his creators, and not eager to return to his eternal task. In the skies, the constellations twist and turn, protesting his absence.

The children in the capital dream restlessly of an endless beast, outpouring from the clouds, large enough to cast a shadow over all the land. They describe a sky serpent that bellows in a million voices, an extinguisher of realms. Cultists and fanatics are again making sacrifice, foretelling that a reckoning will come. They call it the Storm of Souls.

Vigil is overrun by the first winds of this coming storm of undeath. The call again rises for a hero to unite the realms against the many forces that seek to bury everything in despair. The cult must be put down. Samael's remnants must be destroyed before they encroach. The ghostly tide must be quelled, and the forces of all the worlds must form a coalition, before the reckoning arrives.

The storm looms. Who among you will stand before it?"""
            ): """迪奥弗的阴影仍笼罩祈夜。萨麦尔已陨落，但他的所作所为永远伤痕了诸界根基。残存爪牙四散隐匿，密谋作恶。就在祈夜集结对抗这余敌之时，又被新的黑暗所困。幽灵侵扰大地上的人们，它们的到来暗示着更大的威胁。

来自亚哈的访客说，来世本身已陷入动荡。自时间黎明起便接纳亡魂归于终所的守门人凯西斯，已不再值守。如今，躁动而饱受折磨的意志在存在之下翻涌，从世界之间涌出。

守门人在何处？是萨麦尔解除了凯西斯的职责。如今他失踪了，一个连造物主都找不到的叛神幼体，也不愿回到永恒职守。天空中星座扭动翻转，抗议他的缺席。

都城里的孩童不安地梦见一头无尽巨兽从云中倾泻而出，大到能给整片大地投下阴影。他们描述一条以百万嗓音咆哮的天空巨蛇，诸界的熄灭者。邪教徒与狂信者再次献祭，预言清算将至。他们称之为灵魂风暴。

这即将到来的不死风暴的先风已经席卷祈夜。呼唤再次响起：需要一位英雄联合诸界，对抗要把一切埋进绝望的多方势力。教团必须被镇压。萨麦尔的残党必须在扩张之前被摧毁。幽灵潮必须平息，诸世界的力量必须结成同盟，赶在清算到来之前。

风暴将至。你们之中，谁将挺身相迎？""",
        }
    )
    EXACT.update(
        {
            n("<allcaps>Discard Pile:</allcaps>\nPress to switch the view to view your opponent's discard pile."): "<allcaps>弃牌堆：</allcaps>\n点按以查看对手的弃牌堆。",
            n("<allcaps>Hand:</allcaps>\nHow many cards are in your opponent's hand."): "<allcaps>手牌：</allcaps>\n对手手牌的张数。",
            n("<allcaps>Constructs:</allcaps>\nPress to switch the view to your opponent's Constructs."): "<allcaps>神器：</allcaps>\n点按以查看对手的神器。",
            n("<allcaps>Opponent Box:</allcaps>\nPress to expand each oppoent's box to view their cards in detail."): "<allcaps>对手框：</allcaps>\n点按展开每位对手的框，查看其卡牌详情。",
            n("<allcaps>Online Indicator:</allcaps>\nUsed to show an opponent's online status"): "<allcaps>在线指示：</allcaps>\n显示对手的在线状态",
            n("<allcaps>Discard Pile:</allcaps>\nPress to view the cards you've recently played."): "<allcaps>弃牌堆：</allcaps>\n点按查看你最近打出的卡牌。",
            n("<allcaps>End Turn:</allcaps>\nPress this to end your turn and pass to the next player."): "<allcaps>结束回合：</allcaps>\n点按结束你的回合并交给下一位玩家。",
            n("<allcaps>Play All:</allcaps>\nplaces all of the cards from your hand into the Action Area."): "<allcaps>全部打出：</allcaps>\n将手牌全部放入行动区。",
            n("<allcaps>Menu:</allcaps>\nOpens a menu with a list of game options."): "<allcaps>菜单：</allcaps>\n打开包含对局选项的菜单。",
            n("<allcaps>Player's Hand:</allcaps>\nYour current cards that can be played this turn by dragging them to the Action Area."): "<allcaps>玩家手牌：</allcaps>\n你本回合可打出的卡牌，拖到行动区即可打出。",
            n("<allcaps>Construct Tray:</allcaps>\nPress to open your Construct Tray to view and play your Constructs."): "<allcaps>神器托盘：</allcaps>\n点按打开神器托盘，查看并使用你的神器。",
            n("<allcaps>Void:</allcaps>\nDefeated monsters are sent here."): "<allcaps>虚空区：</allcaps>\n被击败的怪物会被送到这里。",
            n("<allcaps>Player's Power:</allcaps>\nPlayer's Power for their turn."): "<allcaps>玩家战力：</allcaps>\n该玩家本回合的战力。",
            n("<allcaps>Player's Runes:</allcaps>\nPlayer's Rune count for their turn."): "<allcaps>玩家符文：</allcaps>\n该玩家本回合的符文数量。",
            n("<allcaps>Player's Energy:</allcaps>\nPlayer's Energy for their turn."): "<allcaps>玩家能量：</allcaps>\n该玩家本回合的能量。",
            n("<allcaps>Center Row:</allcaps>\nThis Center Row contains the cards you can acquire or defeat."): "<allcaps>中央牌列：</allcaps>\n此处是你可以获取或击败的卡牌。",
            n("<allcaps>Center Row Draw Pile:</allcaps>\nThe Center Row cards are drawn from here."): "<allcaps>中央牌库：</allcaps>\n中央牌列的卡牌从此处抽出。",
            n("<allcaps>Global Honor Pool:</allcaps>\nHonor Points for the game are drawn from this pool."): "<allcaps>全局荣誉池：</allcaps>\n对局的荣誉点数从此池抽取。",
            n("<allcaps>Treasure Card:</allcaps>\nAcquiring or defeating center row cards will reward you with all Treasure cards underneath the acquired or defeated card."): "<allcaps>宝藏卡：</allcaps>\n获取或击败中央牌列的卡牌时，你会获得其下方的所有宝藏卡。",
            n("<allcaps>Treasure Count:</allcaps>\nShows the amount of treasure cards available."): "<allcaps>宝藏计数：</allcaps>\n显示可用宝藏卡的数量。",
            n("<allcaps>Event Zone:</allcaps>\nShows the current Event card."): "<allcaps>事件区：</allcaps>\n显示当前事件卡。",
            n("<allcaps>Effect:</allcaps>\nWhat this card does while under a player's control."): "<allcaps>效果：</allcaps>\n此牌在玩家控制下会产生的效果。",
            n("<allcaps>Cost:</allcaps>\nThe Keystone used to gain control of this Temple."): "<allcaps>费用：</allcaps>\n夺取此神殿所用的钥石。",
            "Play Order:": "出牌顺序：",
            "Resources:": "资源：",
            "Game End:": "游戏结束：",
            "Defeating Monsters:": "击败怪物：",
            "Acquiring Heroes and Constructs:": "获取英雄与神器：",
            "Opponent Area": "对手区",
            "Player Area": "玩家区",
            "Top Area": "顶部区域",
            "Info Line": "信息栏",
            "Draw Deck": "抽牌牌库",
            "Honor Points": "荣誉点数",
            "honor points": "荣誉点数",
            "Avatar": "头像",
            "Name": "名称",
            "NAME": "名称",
            "What's New": "新内容",
            "Introduction": "引言",
            "Legendary Track": "传奇轨道",
            "Legendary Status": "传奇地位",
            "Legendary Cards": "传奇卡牌",
            "Gaining Renown": "获得声望",
            "Renown Threshold Effects": "声望阈值效果",
            "Boons": "恩赐",
            "War is Upon Us!": "战争将至！",
            "Dual Cost Cards": "双费卡牌",
            "Light & Dark Cards": "光暗卡牌",
            "New Keywords": "新关键字",
            "Center Row Effects": "中央牌列效果",
            "Keystones": "钥石",
            "Temples": "神殿",
            "Champions & Reputation": "冠军与名望",
            "Champion Card": "冠军卡",
            "Faction Monsters": "派系怪物",
            "Multifaction Heroes & Constructs": "多派系英雄与神器",
            "The Sun Rises On a New World...": "新世界的日出……",
            "Unlock the Secrets of Alosya...": "揭开阿洛西亚的秘密……",
            "Endless possibilities await...": "无尽可能正在等待……",
            "New starting card - Dreamseeker": "新的起始卡——寻梦者",
            "The world will never be the same.": "世界将从此不同。",
            "REPUTATION POWERS\nWays to gain Reputation and rewards for reaching certain tresholds of Reputation.": "名望能力\n获得名望的方式，以及达到特定名望阈值时的奖励。",
            "RARITY & SET ICON\nEach <sprite=146> represents a copy of the card in the center deck.": "稀有度与系列图标\n每个 <sprite=146> 代表中央牌库中该牌的一份复制。",
            "FACTION\nThere are 4 different factions:\n<color=#4cbbeb>Enlightened\n<color=#7fc241>Lifebound\n<color=#b6b6b6>Mechana\n<color=#bb8bbe>Void": "派系\n共有4个不同派系：\n<color=#4cbbeb>圣贤\n<color=#7fc241>命约\n<color=#b6b6b6>机械\n<color=#bb8bbe>虚空",
            "EFFECT\nWhat the card does when played or in play.": "效果\n此牌打出时或在战场上的作用。",
            "REWARD\nWhat this monster does when defeated.": "奖励\n击败此怪物时发生的事。",
            "FLAVOR TEXT\nFlavor text has no game effect.": "风味文本\n风味文本没有游戏效果。",
            "HONOR\nHow much Honor this card is worth.": "荣誉\n此牌值多少荣誉。",
            "COST\nThe amount of Power you must spend to acquire this card.": "费用\n获取此牌必须花费的战力。",
            "COST\nThe number of Runes you must spend to acquire this card.": "费用\n获取此牌必须花费的符文。",
            "Power Card Deck": "战力牌库",
            "Rune Card Deck": "符文牌库",
            "Heroes": "英雄",
            "Constructs": "神器",
            "Monsters": "怪物",
            "Log": "记录",
            "Draw a card.": "抽一张牌。",
            "Draw two cards instead.": "改为抽两张牌。",
            "Enlightened Hero": "圣贤英雄",
            "Lifebound Hero": "命约英雄",
            "Mechana Hero": "机械英雄",
            "Void Hero": "虚空英雄",
            "Enlightened Construct": "圣贤神器",
            "Lifebound Construct": "命约神器",
            "Mechana Construct": "机械神器",
            "Void Construct": "虚空神器",
            "Enlightened Monster": "圣贤怪物",
            "Lifebound Monster": "命约怪物",
            "Mechana Monster": "机械怪物",
            "Void Monster": "虚空怪物",
            "Common Monster": "普通怪物",
        }
    )
    leftover_path = ROOT / "loc" / "en" / "rulebook_leftover.json"
    if leftover_path.is_file():
        items = json.loads(leftover_path.read_text(encoding="utf-8"))
        if len(items) != len(LEFTOVER_ZH):
            print(
                f"warning: leftover count {len(items)} != translations {len(LEFTOVER_ZH)}; "
                f"pairing min length"
            )
        for item, zh in zip(items, LEFTOVER_ZH):
            EXACT[n(item["en"])] = zh

    manual_path = ROOT / "loc" / "zh-Hans" / "rulebook_manual.json"
    if manual_path.is_file():
        for item in json.loads(manual_path.read_text(encoding="utf-8")):
            en = item.get("en") or ""
            zh = item.get("zh") or ""
            if en and zh:
                EXACT[n(en)] = zh
                EXACT[en] = zh
                # Also register runtime-normalized variant without leading newline.
                EXACT[n(en.lstrip("\n"))] = zh


def heading_lookup(text: str, glossary: dict[str, str], names: dict[str, str]) -> str | None:
    t = n(text)
    if t in EXACT:
        return EXACT[t]
    if t in glossary:
        return glossary[t]
    if t.lower() in glossary:
        return glossary[t.lower()]
    plain = n(strip_drop_cap(t))
    if plain in names:
        return names[plain]
    if plain.lower() in names:
        return names[plain.lower()]
    if t.endswith(":") and t[:-1] in glossary:
        return glossary[t[:-1]] + "："
    return None


def translate_row(en: str, glossary: dict[str, str], names: dict[str, str]) -> tuple[str, str]:
    t = n(en)
    if t in SKIP:
        return "", "skip"
    hit = heading_lookup(en, glossary, names)
    if hit:
        return hit, "glossary"
    if t in EXACT:
        return EXACT[t], "rulebook"
    # UI allcaps labels with a following sentence.
    if "<allcaps>" in t.lower() or t[:6].isupper():
        labeled = translate_label(en)
        if labeled != en and re.search(r"[\u4e00-\u9fff]", labeled):
            # still may have English body
            body = translate_effect(labeled)
            if re.search(r"[A-Za-z]{4,}", body):
                body = translate_flavor(body)
            return body, "composed"
    if "Reward" in t or "Fate" in t or "Trophy" in t or "Gain " in t or "<sprite" in t.lower():
        zh = translate_label(translate_effect(en))
        return zh, "effect"
    if len(t) < 80 and not re.search(r"[.!?]", t):
        zh = glossary.get(t) or glossary.get(t.replace(":", ""))
        if zh:
            return zh + ("：" if t.endswith(":") and not zh.endswith("：") else ""), "glossary"
    zh = translate_flavor(en)
    return zh, "flavor"


def main() -> None:
    fill_exact()
    glossary = load_glossary()
    names = load_card_names()
    src_rows = list(csv.DictReader(EN_RB.open(encoding="utf-8", newline="")))
    out_rows = []
    leftover = []
    seen: set[str] = set()
    for row in src_rows:
        en = row["en"]
        key = n(en)
        if key in seen:
            continue
        seen.add(key)
        zh, source = translate_row(en, glossary, names)
        if zh:
            zh = re.sub(r"(?<=[\u4e00-\u9fff])\.$", "。", zh)
        if not zh:
            continue
        latin = len(re.findall(r"[A-Za-z]{4,}", re.sub(r"<[^>]+>", "", zh)))
        if latin >= 3 and source != "skip":
            leftover.append((row["set"], row["go_name"], en[:160], zh[:120]))
        out_rows.append(
            {
                "set": row["set"],
                "go_name": row["go_name"],
                "en": en,
                "norm": row["norm"],
                "zh": zh,
                "source": source,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "go_name", "en", "norm", "zh", "source"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out_rows)} unique)")
    print(f"leftover latin in zh: {len(leftover)}")
    leftover_report = ROOT / "docs" / "rulebook_build_leftover.txt"
    leftover_report.write_text(
        "\n".join(
            f"{a}\t{b}\t{c.replace(chr(10), ' / ')}\t{d.replace(chr(10), ' / ')}"
            for a, b, c, d in leftover
        ),
        encoding="utf-8",
    )
    if leftover:
        print(f"see {leftover_report.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
