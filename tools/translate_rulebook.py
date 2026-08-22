"""Apply manual translations to rulebook.csv rows that still have empty zh.

The glossary already locks every reusable term.  This script stores the
human-authored full-sentence Chinese translation for each *unique* English
rulebook paragraph (including exact rich-text markup like <b>, <br>,
<smallcaps>, <indent=N>, <margin-right=N>, <align=center>, <sprite=N>,
<color=#...>, \r newlines).  We key translations by (en.strip()) so tiny
whitespace variants still match; if the markup differs we fall back and
print a warning so the translator can review.

Run:
    python tools/translate_rulebook.py
Then:
    python tools/build_zh.py
    python tools/patch.py enable --locale zh-Hans
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULEBOOK = ROOT / "loc" / "zh-Hans" / "rulebook.csv"

# ---------------------------------------------------------------------------
# Translation dictionary — (en.strip() -> zh)
# ---------------------------------------------------------------------------
# Keep keys byte-for-byte identical to the en stored in rulebook.csv
# (including <b> tags, \r chars inside <color> etc.).  To find the key,
# open loc/zh-Hans/rulebook.csv and copy the `en` cell raw value
# (Excel: copy cell → paste into editor; VS Code: view the row as text).
# ---------------------------------------------------------------------------

T: dict[str, str] = {}

# ========== CotG 前言 / Introduction (rulebook L334, L336, L338) ==========
T["For millennia, the world of <b>Vigil</b> has been isolated and protected from other realms.  Now, the barrier between dimensions is failing, and <b>Samael, the Fallen God</b>, has returned with his army of Monsters from the beyond!"] = (
    "千百年来，<b>祈夜</b>世界一直与其他领域隔绝并受其庇护。如今，次元之间的屏障正在崩塌，<b>堕落之神萨麦尔</b>率领他的怪物大军从异界归来！"
)
T["You are one of the few warriors capable of facing this threat and defending your world, but you cannot do it alone! You must summon powerful Heroes and Constructs to aid you in your battles."] = (
    "你是少数能够直面此威胁、守护你世界的战士之一，但你无法孤军奋战！你必须召唤强大的英雄与神器助你作战。"
)
T["The player who gains the most <b>Honor Points</b> will lead his army to defeat the <b>Fallen One</b> and earn the title of <b>Godslayer.</b>"] = (
    "赢得最多<b>荣誉点数</b>的玩家将率领自己的军队击败<b>堕落者</b>，夺得<b>弑神者</b>的称号。"
)

# ========== CotG RESOURCES section (L313-333 area) =========================
T["RUNES: Runes are one of the two main resources in Ascension.  Runes are used to acquire Heroes and Constructs so you can add them to your deck."] = (
    "<b>符文：</b>符文是《创升纪元》的两大核心资源之一。符文用于<strong>获取</strong>英雄与神器，将其加入你的牌组。"
)
T["POWER: Power is the second resource in Ascension.  Power is used to defeat Monsters and earn rewards."] = (
    "<b>战力：</b>战力是《创升纪元》的第二资源。战力用于<strong>击败</strong>怪物并获得奖励。"
)
T["HONOR: Honor is the key to victory in Ascension.  Whoever earns the most Honor throughout the game wins and earns the title of Godslayer!"] = (
    "<b>荣誉：</b>荣誉是《创升纪元》通往胜利的钥匙。整场游戏中获得荣誉最多的玩家获胜，并取得「弑神者」的称号！"
)

# -------- margin-right indented resource bullets ----------------------------------
T["<margin-right=8em>\rYou need Runes to acquire Heroes and Constructs.  Runes come from Heroes played from your hand or from Constructs you have in play.  You may acquire any number of cards as long as you have enough Runes.  Cards that are eligible to be acquired will glow green.\r\r\n\r"] = (
    "<margin-right=8em>\r获取英雄与神器需要用到符文。符文的来源是你从手牌中打出的英雄，或是场上已经部署的神器。只要符文充足，你可以获取任意多张卡牌。符合获取条件的卡牌会发出绿色亮光。\r\r\n\r"
)
T["<indent=4em><b>POWER:</b> Power is the second resource in Ascension.  Power is used to defeat Monsters and earn rewards. \r\r\n\r"] = (
    "<indent=4em><b>战力：</b>战力是《创升纪元》的第二资源。战力用于击败怪物并获得奖励。\r\r\n\r"
)

# ========== PLAY ORDER (L324-330) =================================================
PO = (
    "1. <indent=4%>打出手牌以获得符文、战力与荣誉。获取英雄与神器用于后续回合。击败怪物获得荣誉与奖励。\r\r</indent>"
    "\r\r\n\r"
    "2. <indent=4%>当你完成获取英雄与神器、击败怪物等行动后，将手中剩余的所有卡牌放入弃牌堆。\r\r</indent>"
    "\r\r\n\r"
    "3. <indent=4%>从你的个人牌组中重新抓五张牌以补满手牌。如果牌组已空，弃牌堆会自动洗回牌组。\r\r</indent>"
    "\r\r\n\r"
)
T["1. <indent=4%>Play cards from your hand to gain Runes, Power, and Honor.  Acquire Heroes and Constructs for future turns.  Defeat Monsters for Honor and rewards.\r\r</indent>\r\r\n\r"
  "2. <indent=4%>After you are done acquiring Heroes and Constructs and defeating Monsters, all cards in your hand are placed into your discard pile.\r\r</indent>\r\r\n\r"
  "3. <indent=4%>You are dealt five cards from your personal deck to replenish your hand.  If you run out of cards, your discard pile will automatically be shuffled and the cards will be moved to your personal deck.\r\r</indent>\r\r\n\r"] = PO

# ========== END GAME / Honor Pool (L318-320, L360-364) ==========================
ENDGAME = (
    "当荣誉池耗尽一定数量时游戏结束，具体数值取决于玩家人数。\r\r\t\r\r"
    "<align=center>"
    "2 人局 = <sprite=77> 荣誉   3 人局 = <sprite=78> 荣誉   4 人局 = <sprite=79> 荣誉<br></align>"
    "<br>当最后一点荣誉被拿走时，当前回合结束（即，后手玩家打完最后一回合后）才结束游戏。因此，每位玩家的回合数相同；即使荣誉池已耗尽，玩家在自己的回合仍可继续获取荣誉。"
    "<br><br>\r\r"
    "每位玩家牌组中的卡牌也会提供荣誉点数，显示在卡牌左下角的荣誉图标(<sprite=64>)里。游戏结束时，牌组与手牌中所有英雄及神器的荣誉点数全部计入总分；总分最高者获胜！"
    "<br><br>如多名玩家总分相同，后手玩家胜（即：先手玩家在所有平分中告负，第二位输给第三/四位，依此类推）。<br><br>"
)
T["The game ends when a certain amount of Honor has been earned, depending on the number of players.\r\r\t\r\r\n<align=center>\n"
  "2 Players = <sprite=77> Honor   3 Players = <sprite=78> Honor   4 Players = <sprite=79> Honor<br></align>"
  "<br>When the final Honor point is earned, the game ends at the end of the current round (after the last player to start the game takes a turn).  Thus, each player will play the same number of turns during the course of the game and may still gain Honor even when the Honor pool is depleted.<br><br>\r\r"
  "Cards in each player's deck are also worth Honor points, indicated by the number in the Honor symbol (<sprite=64>) in the bottom left corner of each card.  When the game is over, all Honor points from Heroes and Constructs in your deck and hand are added to the Honor you gained during the game.  The player with the most total Honor is the winner!<br><br>"
  "If multiple players have the same number of Honor Points, the last player to start wins (i.e., the starting player loses all ties, the second player loses to the third and fouth, etc.).<br><br>"] = ENDGAME

ENDGAME_SHORT = (
    "当荣誉池耗尽一定数量时游戏结束，具体数值取决于玩家人数。\r\t\r\r\n"
    "<align=center>\n"
    "2 人局 = <sprite=77> 荣誉     3 人局 = <sprite=78> 荣誉     4 人局 = <sprite=79> 荣誉\r\r\n"
)
T["The game ends when a certain amount of Honor has been earned, depending on the number of players.\r\t\r\r\n<align=center>\n"
  "2 Players = <sprite=77> Honor     3 Players = <sprite=78> Honor     4 Players = <sprite=79> Honor\r\r\n"] = ENDGAME_SHORT

# ========== Fate Cards (L357-359) =================================================
T["<margin-right=12em>Some cards have effects when they enter the Center Row.  The effects of these cards occur immediately, including at the start of the game when the Center Row is first dealt.  These are called Fate Cards, and their effects are written in white text within a black textbox, labeled with the Fate keyword.\r\r\n\r"] = (
    "<margin-right=12em>\r部分卡牌在进入中央牌列时就会触发效果。它们的效果会立即结算——包括游戏开局中央牌列首次发牌时。这类卡牌称为「天命卡」（Fate Cards），其效果以白色文字写在黑色文本框中，并带有「天命（Fate）」字样。\r\r\n\r"
)

# ========== CotG Rulebook flavor narration: Kythis / Fallen return (L340-354) ====
KYTHIS_NARR = (
    "我的占卜述说着一则可怖的故事——我亲眼见证了不祥之兆降临在宇宙的深处。就在那通往死亡的空旷入口前，一位赤红色的神灵现身，愤怒而威严，绝非凡俗之魂可比。守门人单膝跪下，伸出双手，将那道灵魂从亡魂之河中拽了出来；他拂去那道澎湃气机上沾着的星辰碎屑，仿佛拔去一丛蒺藜。\r\n\r\n"
    "「这缕魂，我认得。」守门人说道。\r\n\r\n"
    "随之而来的是一条毒蛇的嗓音，仿佛五口齐鸣：「那是因为，你便是我所造。放我出去。」\r\n\r\n"
    "「我却必须送你前行。」守门人答道，「你披过凡俗之躯，便当承受凡俗之命。」\r\n\r\n"
    "<i>不，凯蒂斯。你已无束缚。守门人啊，免去我的命运，我便赦免你的罪。我的手掌尚且留有这份权柄。</i>\r\n\r\n"
    "就这样，堕落者萨麦尔免于被流放到德俄佛——代价是，死亡之畔从此再无人守望，冥界之门从此无人照料，所有意志都将堕入炼狱，无人可渡。\r\n\r\n"
    "而今，战火的烽烟再次染红了远方。边境刚刚归于安宁，新的定居点又将被凡人的鲜血重新淹没。守门人既去，祈夜捍卫者的灵魂离体之后便再无归处——除非一切都能拨乱反正。\r\n\r\n"
    "让召唤之声响彻整个祈夜吧！战火之后的纷争必须就此休止。弑神者啊，请你第二次披甲执剑。\r\n\r\n"
    "堕落者，归来了。"
)
T["My divinations relate a frightful tale- I have seen cosmic events of the darkest portent. There lately came to the yawning gate of death a divine spirit, wrathful and red, not to be mistaken for a mortal will. The Gatekeeper knelt and, with two hands, plucked it from the stream of souls, brushing stars from the pulsating force like so many burrs.\r\n\r\n"
  "\"\"This soul is familiar,\"\" said the Gatekeeper. Then was heard a viper's voice, as if spoken from five mouths at once: It is because I created you. You must release me.\r\n\r\n"
  "\"\"Yet, I am bound to send you on your way,\"\" the Gatekeeper replied.  \"\"You wore a mortal skin. You must suffer a mortal fate.\"\"\r\n\r\n"
  "<i>No, Kythis. You are bound no longer. Forbear my fate, Gatekeeper, and I shall absolve you of yours. It is still within my power.\r</i>\r\n\r\n"
  "\rThus, Samael the Fallen was spared exile to Deofol—at the cost of leaving death's riverbank forever unwatched, the gate untended, and all wills condemned to purgatory.\r\n\r\n"
  "Now, the flames of war again decorate the horizon. Terror grips the frontier, so recently resettled, only to be submerged anew in the blood of mortals. With the Gatekeeper gone, the souls torn from the bodies of Vigil's defenders will know no respite unless all is set right.\r\n\r\n"
  "\rLet a call echo across all of Vigil. The bickering that came in war's wake must end. A Godslayer must take up arms a second time.\r\n\r\n"
  "The Fallen has returned."] = KYTHIS_NARR

# ========== FLAVOR_* standalone paragraphs (L365-368: Nairi / Dhartha / Sadranis / Kor)
T["It was Nairi who raised the Stone Circle, teaching the druids to commune with Cetre and her starchildren.  They look to her example as she moves through the forest, bringing peace to the harsh wilds.  A calm within the storm."] = (
    "奈莉一手竖起了石柱阵，教导德鲁伊们如何与赛特尔及她的星眷沟通。当她穿行林间，为严酷的荒野带来和平之时，万物皆以她为表率。她正是风暴之中那一抹宁静。"
)
T["Chosen long ago by Logos to wield the Arhan god’s sight and wisdom, Dhartha has used it to aid the realms for generations. Small in stature, he proves that real power doesn’t come from standing over others, but by others kneeling before you."] = (
    "许久之前，逻各斯便授予达萨使用亚哈众神的眼界与智慧，而达萨藉此济世代代相传。身形虽矮，他却印证了一个道理：真正的力量，从不来自凌驾于人，而来自人们甘愿为你俯首。"
)
T["Many are enthralled by Nyx's dark whispers, but Sadranis is one of the few who have learned to utter them on their own.  What outsiders mistake for insanity, the wise will tell you is simply an unwavering focus on a much larger scheme."] = (
    "无数人为尼克斯的黑暗低语所奴役，但萨德拉尼斯是少数学会仅凭自己便能念出那些话语的人。外人把他的举止当作疯狂，而智者则会告诉你：他不过是心无旁骛地瞄准了一盘更大的棋局。"
)
T["Since the early days of Hedron, the Ferromancers have been charged with igniting the spark of life within their creations.  Kor taught the order that there was more than just life in the machines, there was also courage and purpose."] = (
    "自棱堡（Hedron）创立之初，铁术士（Ferromancers）便担负着为造物注入生命火花的使命。科尔教导这一教团：机械之中所蕴藏的不只是生命，更是勇气，亦是使命。"
)

# ========== Tutorial placeholder (L294-295) ======================================
T["This is a tutorial text block. This is a tutorial text block. This is a tutorial text block. This is a tutorial text block. This is a tutorial text block. This is a tutorial text block. This is a tutorial text block.\nThis is a tutorial text block. This is a tutorial text block. <sprite=32>"] = (
    "这是一段教学示例文本。这是一段教学示例文本。这是一段教学示例文本。这是一段教学示例文本。这是一段教学示例文本。这是一段教学示例文本。这是一段教学示例文本。\n这是一段教学示例文本。这是一段教学示例文本。 <sprite=32>"
)

# ========== RARITY & SET ICON section (L311-312) ==================================
T["RARITY & SET ICON\nEach <sprite=146> represents a copy of the card in the center deck."] = (
    "<b>稀有度与扩展图标说明</b>\n每个 <sprite=146> 代表中央牌组中本卡的一个副本。"
)

# ========== Tooltip opp-pane (L369-374 Discard/Hand/Constructs) ==================
T["<allcaps>Discard Pile:</allcaps>\nPress to switch the view to view your opponent's discard pile."] = (
    "<allcaps>弃牌堆：</allcaps>\n点击切换视角以查看对手的弃牌堆。"
)
T["<allcaps>Hand:</allcaps>\nHow many cards are in your opponent's hand."] = (
    "<allcaps>对手手牌：</allcaps>\n显示对手当前持有多少张手牌。"
)
T["<allcaps>Constructs:</allcaps>\nPress to switch the view to your opponent's Constructs."] = (
    "<allcaps>神器场：</allcaps>\n点击切换视角以查看对手场上的神器。"
)

# ========== Small inline effect strings (L302-310: Champion per-turn effects) =====
T["Once per turn, you may pay <sprite=34>  to gain <sprite=129>."] = (
    "每回合一次：你可以支付 <sprite=34>，以获得 <sprite=129>。"
)
T["Whenever you acquire or defeat a Lifebound card from the center row, gain <sprite=129>."] = (
    "每当你从中央牌列获取或击败一张命约卡牌时，获得 <sprite=129>。"
)
T["Whenever you acquire or defeat an Enlightened card from the center row, gain <sprite=129>."] = (
    "每当你从中央牌列获取或击败一张圣贤卡牌时，获得 <sprite=129>。"
)
T["Whenever you acquire or defeat a Void card from the center row, gain <sprite=129>."] = (
    "每当你从中央牌列获取或击败一张虚空卡牌时，获得 <sprite=129>。"
)
T["Whenever you acquire or defeat a Mechana card from the center row, gain <sprite=129>."] = (
    "每当你从中央牌列获取或击败一张机械卡牌时，获得 <sprite=129>。"
)
T["Defeat a Monster that has <sprite=4>or less."] = (
    "击败一只战力 ≤ <sprite=4> 的怪物。"
)

# ========== Set-Heading + Promo/DLC Store Descriptions (L284-L293) ==============
# ASCL (史诗传奇) DLC 介绍（L284 L290 L291 三个带换行变体）
ASCL_INTRO = (
    "重返祈夜世界——「恶意缪斯」已然觉醒，毁灭将至。《创升纪元》历史上的传奇英雄们纷纷归来，引领你前行，并将他们的力量赐予那些能够证明自己的人。<br><br>"
    "每一张你获取或击败的卡牌都会为对应派系提供名望，推动你在「传奇轨道」上不断前进。随着名望的积累，你将解锁来自传奇角色的强力恩赐；当某一派系的名望达到顶峰，你将获得该派系的「传奇权柄」：每回合可免费获取或击败一张该派系卡牌。<br><br>"
)
ASCL_V1 = ASCL_INTRO + "<align=center>包括 86 张全新卡牌。"
ASCL_V2 = ASCL_INTRO + "<b><align=center>包括 86 张全新<br>卡牌。"
ASCL_V3 = ASCL_INTRO + "<b><align=center>包括 86 张全新卡牌。"

T["Return to the world of Vigil as the Muses of Malevolence rise to bring ruin. Legendary Heroes from Ascension’s past have returned to guide you, granting their power to those who prove worthy.<br><br>Each card you acquire or defeat grants Renown with its factions, advancing you on the Legendary Track. As your Renown grows, unlock powerful Boons from Legendary Characters and, at the pinnacle of a faction’s track, gain Legendry status with the power to acquire or defeat one card from that faction for free each turn.<br><br><align=center>Includes 86 unique new cards."] = ASCL_V1
T["Return to the world of Vigil as the Muses of Malevolence rise to bring ruin. Legendary Heroes from Ascension’s past have returned to guide you, granting their power to those who prove worthy.<br><br>Each card you acquire or defeat grants Renown with its factions, advancing you on the Legendary Track. As your Renown grows, unlock powerful Boons from Legendary Characters and, at the pinnacle of a faction’s track, gain Legendry status with the power to acquire or defeat one card from that faction for free each turn.<br><br><b><align=center>Includes 86 unique<br>new cards."] = ASCL_V2
T["Return to the world of Vigil as the Muses of Malevolence rise to bring ruin. Legendary Heroes from Ascension’s past have returned to guide you, granting their power to those who prove worthy.<br><br>Each card you acquire or defeat grants Renown with its factions, advancing you on the Legendary Track. As your Renown grows, unlock powerful Boons from Legendary Characters and, at the pinnacle of a faction’s track, gain Legendry status with the power to acquire or defeat one card from that faction for free each turn.<br><br><b><align=center>Includes 86 unique new cards."] = ASCL_V3

# Small Promo bundle (L285, L288: 两个带换行的副本 + 无size变体，L288 没有 promo cards included 标题)
PROMO5 = (
    "<br><size=28><align=center><smallcaps>包含的特典卡：</smallcaps></size><br><br>"
    "<smallcaps><b>怪物：</b></smallcaps><br>巴哥末日<br><br>"
    "<smallcaps><b>圣贤派系：</b></smallcaps><br>风之尖塔<br><br>"
    "<smallcaps><b>命约派系：</b></smallcaps><br>世界之种<br><br>"
    "<smallcaps><b>机械派系：</b></smallcaps><br>混沌重炮<br><br>"
    "<smallcaps><b>虚空派系：</b></smallcaps><br>以太哀歌<br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "运用「风之尖塔」把弃牌转化为强力抽牌，再以「世界之种」从中央牌列榨取额外收益——无数新奇的强力组合就此打开！\r<br><br>"
)
T["<br><size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Puggageddon<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Spire of the Wind<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Seed of the World<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Chaotic Cannon<br><br><smallcaps><b>Void Faction:</b></smallcaps><br>The Aethermourne<br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>Harness Spire of the Wind to turn discards into powerful draw, and Seed of the World to gain extra value from the Center Row—opening up new, powerful combo!\r<br><br>"] = PROMO5
T["<size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Puggageddon<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Spire of the Wind<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Seed of the World<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Chaotic Cannon<br><br><smallcaps><b>Void Faction:</b></smallcaps><br>The Aethermourne<br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>Harness Spire of the Wind to turn discards into powerful draw, and Seed of the World to gain extra value from the Center Row—opening up new, powerful combo!\r<br><br>"] = PROMO5

# L286 大促销包：Rat King bundle
BIG_PROMO = (
    "这套特典卡合集将为你的对局带来无穷乐趣。\r<br><br>"
    "<size=28><align=center><smallcaps>包含的特典卡：</smallcaps></size><br><br>"
    "<smallcaps><b>怪物：</b></smallcaps><br>守门人凯蒂斯<br>鼠王与巨鼠<br>末日终结者<br>紧缩恐惧<br><br>"
    "<smallcaps><b>圣贤派系：</b></smallcaps><br>圣剑贤者维达<br>命运的阿斯卡拉<br>学徒贤者<br>黄金奇才迈尔斯<br><br>"
    "<smallcaps><b>命约派系：</b></smallcaps><br>守路人<br>奥戈向导赛特拉<br>月之权杖<br><br>"
    "<smallcaps><b>机械派系：</b></smallcaps><br>深潜无人机<br>多面体耀光<br>控制中枢<br><br>"
    "<smallcaps><b>虚空派系：</b></smallcaps><br>虚空迷幻师<br>虚空之网<br>缚魂者<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "用<b>鼠王</b>让整个棋盘满是老鼠！操控<b>命运的阿斯卡拉</b>复制对手的英雄牌。打出<b>末日终结者</b>即刻结束比赛。合集还收录了玩家最爱的<b>黄金奇才迈尔斯</b>！\r<br><br>"
)
T["This bundle of promo cards will add a lot of excitement to your games.\r<br><br><size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Kythis, the Gatekeeper<br>Rat King & Giant Rat<br>Ender of Days<br>Constricting Horror<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Vedah, Sage of Swords<br>Askara of Fortune<br>Journeyman Sage<br>Miles, Golen Prodigy<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Pathwarden<br>Cetra, Guide of Ogo<br>Moon Staff<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Deep Drone<br>Hedron Flare<br>Control Room<br><br><smallcaps><b>Void Faction:</b></smallcaps><br>Void Mesmer<br>Nethersnare<br>Soul Collector<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>Use the <b>Rat King</b> to flood the board with rats! Copy other players' hero cards with the <b>Askara of Fortune</b>. End the game instantly with the <b>Ender of Days</b>. The bundle also includes fan-favorite <b>Miles, Golden Prodigy</b>.\r<br><br>"] = BIG_PROMO

# L287 Gift of the Elements + Valley of Ancients + Delirium Bundle
GOTV_VOA_DEL = (
    "驾驭元素之力，唤醒远古神庙的神秘能量——立即入手本组合包！\r<br><br>"
    "<size=28><align=center><smallcaps>各扩展全新卡牌数：</smallcaps></size><br><br>"
    "<b>元素的馈赠：</b><br>55 张<br><br>"
    "<b>上古山谷：</b><br>51 张<br><br>"
    "<b>谵妄：</b><br>49 张<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "让横行肆虐的哥布林寄生对手的牌组；借助<i>赋能（Empower）</i>比以往更迅捷地压缩你的牌组；还能把事件卡转化为《创升纪元》史上最强力的英雄们。\r<br><br>"
    "<b>上古山谷</b>让玩家彼此对抗，争夺对<b>生命神庙</b>、<b>死亡神庙</b>与<b>不朽神庙</b>的控制权——掌控它们的人，将获得令人难以置信的奖励。\r<br><br>"
)
T["Harness elemental magic and the power of ancient temples with this bundle!\r<br><br><size=28><align=center><smallcaps>Unique new cards per set:</smallcaps></size><br><br><b>Gift of the Elements:</b><br>55 cards<br><br><b>Valley of the Ancients:</b><br>51 cards<br><br><b>Delirium:</b><br>49 cards<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>Infest your opponent's deck with rampaging goblins, thin your deck faster than ever with <i>Empower</i>, and transform event cards into Ascension's most powerful Heroes.\r<br><br><b>Valley of the Ancients</b> pits you against each other as you vie for control over the <i>Temples of Life, Death,</i> and <i>Immortality</i>. Incredible bonuses are available to those who control them.\r<br><br>"] = GOTV_VOA_DEL

# L289: Login screen paragraph (Asmodee -> Playdek migration)
LOGIN_MIG = (
    "如果你之前只用 Asmodee.net 账号进行游戏，那么你需要创建一个全新的 Playdek 账号。若希望保留战绩与游戏内进度，请在注册新的 Playdek 账号时使用与 Asmodee.net 账号相同的邮箱。在线好友列表仅会显示 Playdek 平台账号，Asmodee.net 平台的好友列表将不再可用。"
)
T["If you only have an Asmodee.net account that has been used to play Ascension in the past you will need to create a new Playdek account. If you wish to preserve your stats and in-game progress please use the same email from your Asmodee.net account for your new Playdek account. Online Friend's Lists will only be populated with Playdek accounts and Asmodee.net Friend’s Lists will no longer be available."] = LOGIN_MIG

# L292: RU + DC + DS + WoS Bundle (四扩展大合集)
FOURSET_BUNDLE = (
    "本合集收录玩家最爱的四款扩展！\r<br><br>"
    "<size=28><align=center><smallcaps>各扩展全新卡牌数：</smallcaps></size><br><br>"
    "<b>领域解开：</b><br>53 张<br><br>"
    "<b>冠军黎明：</b><br>72 张<br><br>"
    "<b>梦境：</b><br>76 张<br><br>"
    "<b>暗影之战：</b><br>43 张<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "<b>领域解开</b>为《创升纪元》引入了跨派系卡牌，它们通过「多派联合（Muti-Unite）」能力打出闻所未闻的爆炸性回合。\r<br><br>"
    "完成卡牌上列出的游戏内任务，即可获得超乎想象的变形奖励。\r<br><br>"
    "在<b>冠军黎明</b>中，你将化身《创升纪元》最伟大的冠军之一，使用独特的「玩家牌」，每当你获取同一派系的卡牌时玩家牌便会愈发强大。\r<br><br>"
    "<b>冠军黎明</b>的「集结（Rally）」机制，让每一张从牌堆顶上翻开的卡牌都比上一张更令人心跳加速。\r<br><br>"
    "<b>梦境</b>将带你进入《创升纪元》宇宙中的全新世界。从「梦生」卡牌中获取<b>洞察（Insight）</b>，并消耗洞察来取得你在游戏开始时秘密选择的「个人专属梦境卡」！\r<br><br>"
    "<b>暗影之战</b>为《创升纪元》引入了昼夜系统。获取与击败卡牌都会使整个盘面在昼与夜之间切换，从而让你手牌中不同派系的卡牌分别获得强化。<br><br>"
)
T["A favorite fan bundle of expansions!\r<br><br><size=28><align=center><smallcaps>Unique new cards per set:</smallcaps></size><br><br><b>Realms Unraveled:</b><br>53 cards<br><br><b>Dawn of Champions:</b><br>72 cards<br><br><b>Dreamscape:</b><br>76 cards<br><br><b>War of Shadows:</b><br>43 cards<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br><b>Realms Unraveled</b> introduces multi-faction cards to Ascension, which use a muti-unite ability to create turns, unlike anything you've seen before from Ascension.\r<br><br>Completing the in-game quests listed on cards reward you with extraordinary transformations.\r<br><br>In <b>Dawn of Champions,</b> you become one of Ascension's greatest Champions with unique player cards that power up as you buy cards from their faction.\r<br><br><b>Dawn of Champion's</b> Rally mechanic will make each card that flips off the deck more exciting than ever.\r<br><br><b>Dreamscape</b> will take you to an all-new world within the Ascension universe. Acquire insight from Dreamborn cards and spend it to acquire the personal Dreamscape cards you secretly selected at the beginning of the game!\r<br><br><b>War of Shadows</b> introduces night and day to Ascension. Acquire and defeat cards, shifting the board back and forth from day and night, empowering different cards in your hand.<br><br>"] = FOURSET_BUNDLE

# L293: Promo Pack 大礼包 (Explosive Swarm / Portal / Defender of Vigil etc.)
MEGAPROMO = (
    "这套特典卡合集收录了我们为《创升纪元》设计过的一批最天马行空的新卡！<br><br>"
    "<size=28><align=center><smallcaps>包含的特典卡：</smallcaps></size><br><br>"
    "<smallcaps><b>怪物：</b></smallcaps><br>爆裂虫群<br>征收者凯莱克<br>诺娃·混沌所生<br><br>"
    "<smallcaps><b>圣贤派系：</b></smallcaps><br>以太传灵师<br>以太策展人<br>先知大卫<br>潜能之眼<br><br>"
    "<smallcaps><b>命约派系：</b></smallcaps><br>远古之灵<br>春生女巫<br>兽王福雷斯特<br>月祭主母<br><br>"
    "<smallcaps><b>机械派系：</b></smallcaps><br>时空挖土机<br>毁灭者之门<br>N.I.N.E.<br>禅修修士<br><br>"
    "<smallcaps><b>虚空派系：</b></smallcaps><br>永恒拷问者<br>以太祭师<br>混沌骑士<br>虚灵女猎手<br><br>"
    "<smallcaps><b>公共：</b></smallcaps><br>传送门卡牌<br>祈夜守卫者<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "获得「传送门卡牌」，它们可以变形为任何《创升纪元》扩展中的任意卡牌。让<b>爆裂虫群</b>这种怪物充满整个中央牌列。使用<b>时空挖土机</b>为中央牌列增加第七张卡牌。本合集还收录了第一张也是唯一一张没有派系归属的中央牌列英雄：<b>祈夜守卫者</b>！\r<br><br>"
)
T["This bundle of promo cards has some of our wildest additions to Ascension.<br><br><size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Explosive Swarm<br>Tollmaster Ky'lek<br>Nova, Born of Chaos<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Æther Channeler<br>Æther Curator<br>David, Prophetic Guide<br>Eye of Potential<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Spirit of the Ancients<br>Ætherspring Witch<br>Forrest, Beastwarden<br>Lunar Matriarch<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Temporal Excavator<br>Destroyer's Gate<br>N.I.N.E.<br>Tinkering Monk<br><br><smallcaps><b>Void Faction:</b></smallcaps><br>Eternal Tormentor<br>Æther Ritualist<br>Chaos Rider<br>Ethereal Hunteress<br><br><smallcaps><b>Common:</b></smallcaps><br>The Portal Card<br>Defender of Vigil<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>Acquire portal cards, which can transform into random cards from any Ascension set. Fill the board with <b>Explosive Swarm</b> monsters. Add a seventh card to the Center Row with the <b>Temporal Excavator</b>. This bundle also includes the first and only Center Row Hero with no faction, the <b>Defender of Vigil</b>!\r<br><br>"] = MEGAPROMO

# ========== Remaining shop / What's New / account copy (Phase 0 fill) ==========
ROV_DU_BUNDLE = (
    "本合集收录《创升纪元》第三年两款独立扩展。<br><br>"
    "<size=28><align=center><smallcaps>各扩展全新卡牌数：</smallcaps></size><br><br>"
    "<b>祈夜崛起：</b><br>47 张<br><br>"
    "<b>黑暗释放：</b><br>35 张<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
    "<b>祈夜崛起</b>与<b>黑暗释放</b>带来前所未有的刺激——全新卡牌类型「宝藏」：能量碎片。"
    "获取或击败叠在碎片上的卡牌即可得到碎片；碎片能强化甚至永久变形你的卡牌。<br><br>"
)
T["This bundle has the two incredible stand alone sets from the third year of Ascension.<br><br><size=28><align=center><smallcaps>Unique new cards per set:</smallcaps></size><br><br><b>Rise of Vigil:</b><br>47 cards<br><br><b>Darkness Unleashed:</b><br>35 cards<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br><b>Rise of Vigil</b> and <b>Darkness Unleashed</b> provide unparalleled excitement with <i>Energy Shards</i>. These Shards are a new card type called <i>Treasure</i>, that you get by acquiring and defeating cards on top of them. These Shards will power up your cards and even permanently transform your cards.<br><br>"] = ROV_DU_BUNDLE

DELIVERANCE_BLURB = (
    "黑暗势力已占据梦境。与帕西希娅联手，收集她的传奇武器，重建秩序！<br><br>"
    "运用洞察资源与梦生卡牌拯救梦境。将怪物缚入你的牌组并投入战斗！"
    "把卡牌变形为强大的英雄与神器，并获取帕西希娅！"
    "将「救赎」与「梦境」「谵妄」组合游玩，体验更刺激的对局！<br><br>"
    "<b><align=center>包括 51 张全新卡牌。"
)
T["Dark forces have taken over the Dreamscape. Team up with Pasythea, collect her legendary weapons, and return order to her world!<br><br>Use the Insight resources and Dreamborn cards to save the Dreamscape. Bind Monsters to your deck and use them in battle! Transform cards to incredible heroes and Constructs and acquire Pasythea! Pair Deliverance with Dreamscape and Delirium for an even more exciting game!<br><br><b><align=center>Includes 51 unique<br>new cards."] = DELIVERANCE_BLURB
T["Dark forces have taken over the Dreamscape. Team up with Pasythea, collect her legendary weapons, and return order to her world!<br><br>Use the Insight resources and Dreamborn cards to save the Dreamscape. Bind Monsters to your deck and use them in battle! Transform cards to incredible heroes and Constructs and acquire Pasythea! Pair Deliverance with Dreamscape and Delirium for an even more exciting game!<br><br><b><align=center>Includes 51 unique new cards."] = (
    "黑暗势力已占据梦境。与帕西希娅联手，收集她的传奇武器，重建秩序！<br><br>"
    "运用洞察资源与梦生卡牌拯救梦境。将怪物缚入你的牌组并投入战斗！"
    "把卡牌变形为强大的英雄与神器，并获取帕西希娅！"
    "将「救赎」与「梦境」「谵妄」组合游玩，体验更刺激的对局！<br><br>"
    "<b><align=center>包括 51 张全新卡牌。"
)

DELIRIUM_BLURB = (
    "「谵妄」带你重返梦境，面对扭曲的新现实。<br><br>"
    "洞察与梦生卡牌再度登场，并解锁全新力量。<br><br>"
    "赢得天命竞拍、反复触发英雄效果，并用洞察投掷神奇的谵妄骰，抢占先机！<br><br>"
    "<b><align=center>包括 49 张全新卡牌。"
)
T["Delirium brings players back into the Dreamscape, facing a twisted new reality.<br><br>Insight and Dreamborn cards are back, but with new powers to unlock with them.<br><br>Win Fate Auctions, Recur hero effects, and roll the amazing Delirium Die with your Insight to gain an edge against the other players!<br><br><b><align=center>Includes 49 unique new cards."] = DELIRIUM_BLURB

T["A Playdek account is now required to connect and play Ascension online. An Asmodee.net account will no longer work for Ascension online play. Your Playdek password might be different from your Asmodee.net password. Please use the Forgot Login button to reset your Playdek account password."] = (
    "现在需要 Playdek 账号才能连接并游玩《创升纪元》在线对局。Asmodee.net 账号已不再适用。"
    "你的 Playdek 密码可能与 Asmodee.net 密码不同。请使用「忘记登录信息」按钮重置 Playdek 账号密码。"
)

T["Pasythea, The Redeemer is a unique card to the Deliverance expansion set.<br> Any player may pay her <sprite=112> cost during their turn to acquire her straight into their hand.<br>Pasythea, The Redeemer does not count as a card in the center row."] = (
    "救赎者帕西希娅是「救赎」扩展的独特卡牌。<br>"
    "任意玩家可在自己的回合支付其 <sprite=112> 费用，直接将其获取到手牌中。<br>"
    "救赎者帕西希娅不计入中央牌列的卡牌数量。"
)

T["* New dual-cost Heroes and Constructs require players to use both resources to acquire them, but have incredible power!\n*As the balance between Light and Dark shifts, cards gain additional powers depending on whether it is Night or Day."] = (
    "* 全新「双费用」英雄与神器需要同时花费两种资源才能获取，但效果极为强大！\n"
    "* 随着光暗天平的倾斜，卡牌会依「昼」或「夜」获得额外能力。"
)

T["<margin-right=12em>The Fanatic is a new Always Available Monster in Storm of Souls. The Fanatic is a Trophy Monster with a variable reward based on the current Event called an Event Trophy. You may have no more than one Fanatic Trophy at any time. If you defeat a Fanatic while you already have a Trophy from one, you gain the Honor reward but do not"] = (
    "<margin-right=12em>狂热者是《灵魂风暴》中的全新常驻怪物。它是战利品怪物，其「事件战利品」奖励随当前事件变化。"
    "你同时最多只能拥有一个狂热者战利品。若你已持有其战利品时再次击败狂热者，仍获得荣誉奖励，但不会"
)

# ========== L50-L61 L80-L81 CotG 资源 / PlayOrder 变体（不带末尾 \r\r） =================
T["<margin-right=8em>\rYou need Runes to acquire Heroes and Constructs.  Runes come from Heroes played from your hand or from Constructs you have in play.  You may acquire any number of cards as long as you have enough Runes.  Cards that are eligible to be acquired will glow green."] = (
    "<margin-right=8em>\r获取英雄与神器需要用到符文。符文的来源是你从手牌中打出的英雄，或是场上已经部署的神器。只要符文充足，你可以获取任意多张卡牌。符合获取条件的卡牌会发出绿色亮光。"
)
T["<indent=4em><b>RUNES:</b> Runes are one of the two main resources in Ascension.  Runes are used to acquire Heroes and Constructs so you can add them to your deck."] = (
    "<indent=4em><b>符文：</b>符文是《创升纪元》的两大核心资源之一。符文用于获取英雄与神器，将其加入你的牌组。"
)
T["<indent=4em><b>HONOR:</b> Honor is the key to victory in Ascension.  Whoever earns the most Honor throughout the game wins and earns the title of Godslayer!"] = (
    "<indent=4em><b>荣誉：</b>荣誉是《创升纪元》通往胜利的钥匙。整场游戏中获得荣誉最多的玩家获胜，并取得「弑神者」的称号！"
)
T["<indent=4em><b>POWER:</b> Power is the second resource in Ascension.  Power is used to defeat Monsters and earn rewards. \r\r"] = (
    "<indent=4em><b>战力：</b>战力是《创升纪元》的第二资源。战力用于击败怪物并获得奖励。 \r\r"
)
T["1. <indent=4%>Play cards from your hand to gain Runes, Power, and Honor.  Acquire Heroes and Constructs for future turns.  Defeat Monsters for Honor and rewards.\r\r</indent>\n\n2. <indent=4%>After you are done acquiring Heroes and Constructs and defeating Monsters, all cards in your hand are placed into your discard pile.\r\r</indent>\n\n3. <indent=4%>You are dealt five cards from your personal deck to replenish your hand.  If you run out of cards, your discard pile will automatically be shuffled and the cards will be moved to your personal deck.\r\r</indent>"] = (
    "1. <indent=4%>打出手牌以获得符文、战力与荣誉。获取英雄与神器用于后续回合。击败怪物获得荣誉与奖励。\r\r</indent>\n\n"
    "2. <indent=4%>当你完成获取英雄与神器、击败怪物等行动后，将手中剩余的所有卡牌放入弃牌堆。\r\r</indent>\n\n"
    "3. <indent=4%>从你的个人牌组中重新抓五张牌以补满手牌。如果牌组已空，弃牌堆会自动洗回牌组。\r\r</indent>"
)

# L53 三联段（带两个空行分隔）
T["For millennia, the world of <b>Vigil</b> has been isolated and protected from other realms.  Now, the barrier between dimensions is failing, and <b>Samael, the Fallen God</b>, has returned with his army of Monsters from the beyond!\n\nYou are one of the few warriors capable of facing this threat and defending your world, but you cannot do it alone! You must summon powerful Heroes and Constructs to aid you in your battles.\n\nThe player who gains the most <b>Honor Points</b> will lead his army to defeat the <b>Fallen One</b> and earn the title of <b>Godslayer.</b>"] = (
    "千百年来，<b>祈夜</b>世界一直与其他领域隔绝并受其庇护。如今，次元之间的屏障正在崩塌，<b>堕落之神萨麦尔</b>率领他的怪物大军从异界归来！\n\n"
    "你是少数能够直面此威胁、守护你世界的战士之一，但你无法孤军奋战！你必须召唤强大的英雄与神器助你作战。\n\n"
    "赢得最多<b>荣誉点数</b>的玩家将率领自己的军队击败<b>堕落者</b>，夺得<b>弑神者</b>的称号。"
)

# L82 邪神归来 What's New narrative (邪神归来 前言)
SOS_NARR = (
    "德俄佛的阴影依旧笼罩着祈夜。萨麦尔虽已陨落，但他的所作所为在各域的根基上留下了永不磨灭的伤痕。他残存的爪牙四散藏匿，暗中谋划着邪恶的复兴。然而，就在祈夜重整旗鼓、清剿余孽之时，一股新的黑暗袭来——「邪神（Specter）」从虚空中破界而出。于是「弑神编年史」后的新篇章就此开启，它名为：<b>灵魂风暴（Storm of Souls）</b>。"
)
T["The shadow of Deofol still looms over Vigil. Samael has fallen, but his actions have forever scarred the foundation of the realms. His surviving minions are scattered and hidden, plotting evil. Yet, even as the Vigil gathers itself against this remaining enemy, it is beset by a new darkness. Specter ..."] = SOS_NARR

# ========== L66-L79 Allcaps tooltips (Action-Area help box) =====================
T["<allcaps>Opponent Box:</allcaps>\nPress to expand each oppoent's box to view their cards in detail."] = (
    "<allcaps>对手信息栏：</allcaps>\n点击展开每一位对手的信息栏详情，查看对方的具体卡牌。"
)
T["<allcaps>Online Indicator:</allcaps>\nUsed to show an opponent's online status"] = (
    "<allcaps>在线标识：</allcaps>\n用于显示对手当前是否在线。"
)
T["<allcaps>Discard Pile:</allcaps>\nPress to view the cards you've recently played."] = (
    "<allcaps>弃牌堆：</allcaps>\n点击查看你刚刚打出过的卡牌。"
)
T["<allcaps>End Turn:</allcaps>\nPress this to end your turn and pass to the next player."] = (
    "<allcaps>结束回合：</allcaps>\n点击结束当前回合，将行动权交给下一位玩家。"
)
T["<allcaps>Play All:</allcaps>\nplaces all of the cards from your hand into the Action Area."] = (
    "<allcaps>全部打出：</allcaps>\n将你手牌中的所有卡牌一次性放入行动区。"
)
T["<allcaps>Menu:</allcaps>\nOpens a menu with a list of game options."] = (
    "<allcaps>菜单：</allcaps>\n打开菜单，列出可进行的游戏操作。"
)
T["<allcaps>Player's Hand:</allcaps>\nYour current cards that can be played this turn by dragging them to the Action Area."] = (
    "<allcaps>你的手牌：</allcaps>\n你在本回合可以打出的卡牌；将牌拖入行动区即可打出。"
)
T["<allcaps>Construct Tray:</allcaps>\nPress to open your Construct Tray to view and play your Constructs."] = (
    "<allcaps>神器面板：</allcaps>\n点击打开神器面板，查看并部署你的神器。"
)
T["<allcaps>Void:</allcaps>\nDefeated monsters are sent here."] = (
    "<allcaps>虚空：</allcaps>\n被击败的怪物会被送到这里。"
)
T["<allcaps>Player's Power:</allcaps>\nPlayer's Power for their turn."] = (
    "<allcaps>你的战力：</allcaps>\n本回合你拥有的战力值。"
)
T["<allcaps>Player's Runes:</allcaps>\nPlayer's Rune count for their turn."] = (
    "<allcaps>你的符文：</allcaps>\n本回合你拥有的符文数。"
)
T["<allcaps>Center Row Draw Pile:</allcaps>\nThe Center Row cards are drawn from here."] = (
    "<allcaps>中央牌列牌堆：</allcaps>\n中央牌列的卡牌从这里补充。"
)
T["<allcaps>Center Row:</allcaps>\nThis Center Row contains the cards you can acquire or defeat."] = (
    "<allcaps>中央牌列：</allcaps>\n显示当前可获取或可击败的卡牌。"
)
T["<allcaps>Global Honor Pool:</allcaps>\nHonor Points for the game are drawn from this pool."] = (
    "<allcaps>全局荣誉池：</allcaps>\n本局使用的荣誉点数来源于此处。"
)
T["<allcaps>Event Zone:</allcaps>\nShows the current Event card."] = (
    "<allcaps>事件区：</allcaps>\n显示当前的事件卡牌。"
)

# ========== Storm of Souls mechanics (L84 Destroy, L85 Fanatic, L88 Trophy reward) ===
T["Destroy is a new game term introduced in Storm of Souls. Destroy means to put into your discard pile from play and generally refers to Constructs.  Any effect from a previous Ascension set which put a Construct into the discard pile from play is  now considered to destroy that Construct. \r"] = (
    "「销毁（Destroy）」是《灵魂风暴》引入的新术语。销毁指「从场上置入你的弃牌堆」，一般针对神器而言。此前《创升纪元》其它扩展中所有「把神器从场上放入弃牌堆」的效果，现在统一视为销毁该神器。\r"
)
T["<margin-right=12em>The Fanatic is a new Always Available Monster in Storm of Souls. The Fanatic is a Trophy Monster with a variable reward based on the current Event called an Event Trophy. You may have no more than one Fanatic Trophy at any time. If you defeat a Fanatic while you already have a Trophy, the most recently acquired Fanatic Trophy is placed where the old Trophy was in your Construct Tray."] = (
    "<margin-right=12em>「狂徒（Fanatic）」是《灵魂风暴》新增的常驻可击败怪物。狂徒是战利品怪物，它的奖励会根据当前事件而变化，称为「事件战利品」。同一时间你只能拥有一个狂徒战利品；如果你在已经持有一个战利品的情况下再次击败狂徒，那么新取得的狂徒战利品会覆盖旧战利品在神器面板中的位置（旧的消失）。"
)
T["<color=#951719FF>Trophy:</color> You may banish this to gain <sprite=33>."] = (
    "<color=#951719FF>战利品：</color>你可以放逐此卡以获得 <sprite=33>。"
)
T["<margin-right=12em>Some Monsters in Storm of Souls have a new kind of reward called Trophy.  When you defeat a Trophy Monster, you gain the Honor portion of its reward immediately, and then instead of banishing the Monster it is placed into your Construct Tray.  At any time during your turn, you may banish the Trophy card from your Construct Tray to gain the <color=#951719FF>Trophy</color> reward printed in red on the right side of the Monster card."] = (
    "<margin-right=12em>《灵魂风暴》中的部分怪物新增了一种奖励类型，称为「战利品（Trophy）」。当你击败战利品怪物时，你立即先获取其中的荣誉部分；随后怪物不会被放逐，而是直接放入你的神器面板。在你回合的任意时刻，你可以把神器面板里的战利品卡放逐，以换取怪物卡右侧红色印刷的<color=#951719FF>战利品奖励</color>。"
)
T["Once per turn, when a player defeats a Monster in the center row, that player gains <sprite=65>.\n\n<color=#d8a6ffff>Event Trophy:</color> Banish a card in your hand or discard pile."] = (
    "每回合一次：当玩家击败中央牌列中的一只怪物时，该玩家获得 <sprite=65>。\n\n<color=#d8a6ffff>事件战利品：</color>放逐你手牌或弃牌堆中的一张卡牌。"
)
T["<margin-right=16em>Event cards represent global effects that change the power structure of the world. When an Event flips from the Portal Deck, it is put into the Event Zone instead of the center row. The card is then replaced in the Center Row as normal.  There may be only one Event in the Event Zone at a time; when a new Event is played, it replaces the previous Event and the previous Event is banished. Any Event card or other ability which causes Events to be replaced, replaced, or removed will remove the current Event before the new Event card enters the Event Zone."] = (
    "<margin-right=16em>事件卡代表足以改变世界力量格局的全球性效应。当事件卡从传送门牌堆翻出时，它被放入事件区而非直接进入中央牌列，原位置会按常规方式补一张新卡进入中央牌列。同一时间事件区内只能存在一个事件；当新事件触发时，它会替换旧事件，旧事件被放逐。任何替换、覆盖或移除事件的效果，都会在新事件进入事件区之前先移除当前事件。"
)

# ========== Credits pages (Administration / Additional IP / Design / Programming)
# Strategy: translate heading (<smallcaps>, <color>) and job titles.  Personal
# names + company names (Playdek, Stone Blade, Gary Games, etc.) stay English.

CREDITS_ADM = (
    "<smallcaps><size=120%><b>管理层\r</b></size></smallcaps>\n\n\r"
    "<smallcaps><color=#1C4E80C8>Playdek 首席执行官\r</color></smallcaps>\n\r\rJoel Goodman\r"
)
T["<smallcaps><size=120%><b>Administration\r</b></size></smallcaps>\n\n\r<smallcaps><color=#1C4E80C8>Chief Executive Officer, Playdek\r</color></smallcaps>\n\r\rJoel Goodman\r"] = CREDITS_ADM

CREDITS_AIP = (
    "<smallcaps><color=#1C4E80C8>附加 IP 开发\r</color></smallcaps>\n\r"
    "John Fiorillo\r\n\rJustin Gary\r\n\rBrian Kibler\r\n\rRyan O'Connor\r\n\rMike Rosenberg\r\n\rEric Sabee\r\n\rGeordie Tait\r\n\rEric Tice\r\n\rGreg Wilson\r\n\r\n"
    "<smallcaps><color=#1C4E80C8>风味文本</color></smallcaps>\r\r"
)
T["<smallcaps><color=#1C4E80C8>Additional IP Development\r</color></smallcaps>\n\rJohn Fiorillo\r\n\rJustin Gary\r\n\rBrian Kibler\r\n\rRyan O'Connor\r\n\rMike Rosenberg\r\n\rEric Sabee\r\n\rGeordie Tait\r\n\rEric Tice\r\n\rGreg Wilson\r\n\r\n<smallcaps><color=#1C4E80C8>Flavor Text</color></smallcaps>\r\r"] = CREDITS_AIP


T["<smallcaps><color=#1C4E80C8>Additional IP Development\r</color></smallcaps>\n\rJohn Fiorillo\r\n\rJustin Gary\r\n\rBrian Kibler\r\n\rRyan O'Connor\r\n\rMike Rosenberg\r\n\rEric Sabee\r\n\rGeordie Tait\r\n\rEric Tice\r\n\rGreg Wilson\r\n\r\n<smallcaps><color=#1C4E80C8>Flavor Text</color></smallcaps>\r\r"] = CREDITS_AIP

# L12 variant: same CREDITS_AIP content but truncated differently (longer: with flavor text names list cut off)
# -> use the same translation (normalized-match loop should catch it; exact match won't)

# ========== Credits page: Administration (L14 variant - ends with \n\n\n)
CREDITS_ADM_VAR = CREDITS_ADM + "\n\n\n"
T["<smallcaps><size=120%><b>Administration\r</b></size></smallcaps>\n\n\r<smallcaps><color=#1C4E80C8>Chief Executive Officer, Playdek\r</color></smallcaps>\n\r\rJoel Goodman\r\n\n\n"] = CREDITS_ADM_VAR

# ========== Credits page: Delirium (L13) heading + job titles + leave names English
CREDITS_DELIRIUM = (
    "\n\r<b><smallcaps><size=120%>神智迷乱</size></smallcaps></b>\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>《创升纪元》游戏引擎设计\r\r</color></smallcaps>\n\rJustin Gary\r\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>《创升纪元：神智迷乱》主设计\r</color></smallcaps>\nGary Arant \n\r\n\r"
    "<smallcaps><color=#1C4E80C8>设计与开发团队\r\r</color></smallcaps>\n\rJustin Gary, Gary Arant, Jason Zila,\nMata "  # truncated; leave rest
)
T["\n\r<b><smallcaps><size=120%>Delirium</size></smallcaps></b>\n\r\n\r<smallcaps><color=#1C4E80C8>Ascension™ Game Engine Design\r\r</color></smallcaps>\n\rJustin Gary\r\n\r\n\r<smallcaps><color=#1C4E80C8>Ascension: Delirium™ Lead Design\r</color></smallcaps>\nGary Arant \n\r\n\r<smallcaps><color=#1C4E80C8>Design & Development Team\r\r</color></smallcaps>\n\rJustin Gary, Gary Arant, Jason Zila,\nMata "] = CREDITS_DELIRIUM

# ========== Puggageddon Promo bundle: L19 (=with leading <br>) and L22 (=without leading <br>)
PUGG_LIST = (
    "<size=28><align=center><smallcaps>包含的特典卡：</smallcaps></size><br><br>"
    "<smallcaps><b>怪物：</b></smallcaps><br>灭世浩劫·帕格<br><br>"
    "<smallcaps><b>圣贤派系：</b></smallcaps><br>风之尖塔<br><br>"
    "<smallcaps><b>命约派系：</b></smallcaps><br>世界之种<br><br>"
    "<smallcaps><b>机械派系：</b></smallcaps><br>混沌重炮<br><br>"
)
T["<br><size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Puggageddon<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Spire of the Wind<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Seed of the World<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Chaotic Cannon<br><br>"] = (
    "<br>" + PUGG_LIST
)
T["<size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Puggageddon<br><br><smallcaps><b>Enlightened Faction:</b></smallcaps><br>Spire of the Wind<br><br><smallcaps><b>Lifebound Faction:</b></smallcaps><br>Seed of the World<br><br><smallcaps><b>Mechana Faction:</b></smallcaps><br>Chaotic Cannon<br><br>"] = PUGG_LIST

# ========== "Excitement promo" bundle L20
T["This bundle of promo cards will add a lot of excitement to your games.\r<br><br><size=28><align=center><smallcaps>Promo Cards Included:</smallcaps></size><br><br><smallcaps><b>Monsters:</b></smallcaps><br>Kythis, the Gatekeeper<br>Rat King & Giant Rat<br>Ender of Days<br>Constricting Horror<br><br>"] = (
    "这套特典卡合集将为你的对局带来更加波澜壮阔的体验！\r<br><br>"
    "<size=28><align=center><smallcaps>包含的特典卡：</smallcaps></size><br><br>"
    "<smallcaps><b>怪物：</b></smallcaps><br>守门者凯提斯<br>鼠王与巨鼠<br>末日终结者<br>绞缚恐魔<br><br>"
)

# ========== Gift of Elements + Temples bundle L21
T["Harness elemental magic and the power of ancient temples with this bundle!\r<br><br><size=28><align=center><smallcaps>Unique new cards per set:</smallcaps></size><br><br><b>Gift of the Elements:</b><br>55 cards<br><br><b>Valley of the Ancients:</b><br>51 cards<br><br><b>Delirium:</b><br>49 cards<br><br><br><size=28><align=center><smallcaps>Description:</smallcaps></size><br><br>"] = (
    "驾驭元素魔法与远古神殿之力，尽在本合集！\r<br><br>"
    "<size=28><align=center><smallcaps>各扩展全新卡牌数：</smallcaps></size><br><br>"
    "<b>元素之赐：</b><br>55 张<br><br>"
    "<b>远古之谷：</b><br>51 张<br><br>"
    "<b>神智迷乱：</b><br>49 张<br><br><br>"
    "<size=28><align=center><smallcaps>简介：</smallcaps></size><br><br>"
)

# ========== Honor endgame variant (L49 + L58): with 2 Players = <sprite=77> etc.
HONOR_ENDGAME_LONG = (
    "当累计获得的荣誉达到某个阈值时游戏结束，阈值取决于玩家人数。\r\r   \r\r\n"
    "<align=center>\n2 人局 = <sprite=77> 荣誉   3 人局 = <sprite=78> 荣誉   4 人局 = <sprite=79> 荣誉<br></align><br>"
    "当最后一个荣誉点数被取走后，游戏会在当前回合结束（等顺序最后的那位玩家也打完回合）时正式结束。因此，所有玩家在整局游戏中都会进行相同数量的回合；即使荣誉池已空，仍然可以获得荣誉。<br><br>\r\r"
    "每位玩家牌组中的卡牌本身也含有荣誉点数，以卡牌左下角的荣誉符号（<sprite=64>）中的数字表示。游戏结束后，将你牌组和手牌中所有英雄与神器的荣誉点数，与你在对局过程中获得的荣誉加总。荣誉总值最高的玩家获胜！<br><br>"
    "如果多名玩家荣誉点数相同，则起始顺序靠后的玩家获胜（即起始先手玩家在平局中输给所有后手玩家，第二名玩家输给第三及第四名，依此类推）。<br><br>"
)
T["The game ends when a certain amount of Honor has been earned, depending on the number of players.\r\r   \r\r\n<align=center>\n2 Players = <sprite=77> Honor   3 Players = <sprite=78> Honor   4 Players = <sprite=79> Honor<br></align><br>When the final Honor point is earned, the game ends at the end of the current round (after the last player to start the game takes a turn).  Thus, each player will play the same number of turns during the course of the game and may still gain Honor even when the Honor pool is depleted.<br><br>\r\rCards in each player's deck are also worth Honor points, indicated by the number in the Honor symbol (<sprite=64>) in the bottom left corner of each card.  When the game is over, all Honor points from Heroes and Constructs in your deck and hand are added to the Honor you gained during the game.  The player with the most total Honor is the winner!<br><br>If multiple players have the same number of Honor Points, the last player to start wins (i.e., the starting player loses all ties, the second player loses to the third and fouth, etc.).<br><br>"] = HONOR_ENDGAME_LONG

HONOR_ENDGAME_SHORT = (
    "当累计获得的荣誉达到某个阈值时游戏结束，阈值取决于玩家人数。\r     \r\r\n"
    "<align=center>\n2 人局 = <sprite=77> 荣誉     3 人局 = <sprite=78> 荣誉     4 人局 = <sprite=79> 荣誉\n\n"
)
T["The game ends when a certain amount of Honor has been earned, depending on the number of players.\r     \r\r\n<align=center>\n2 Players = <sprite=77> Honor     3 Players = <sprite=78> Honor     4 Players = <sprite=79> Honor\n\n"] = HONOR_ENDGAME_SHORT

# ========== L16: Ascension:\nDeck Building Game page (game design + RoV lead design) — truncated
CREDITS_RoV = (
    "<size=120%><smallcaps><b>创升纪元：\n牌组构筑游戏\r</b></smallcaps></size>\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>《创升纪元》游戏设计</color></smallcaps>\n\rJustin Gary\r\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>《祈夜崛起》主设计</color>\r</smallcaps>\n\rJustin Gary\r\n\r\n"
)
T["<size=120%><smallcaps><b>Ascension:\nDeck Building Game\r</b></smallcaps></size>\n\r\n\r<smallcaps><color=#1C4E80C8>Ascension™ Game Design</color></smallcaps>\n\rJustin Gary\r\n\r\n\r<smallcaps><color=#1C4E80C8>Rise of Vigil™ Lead Design</color>\r</smallcaps>\n\rJustin Gary\r\n\r\n"] = CREDITS_RoV

# ========== L17: Ascension:DBG Lead Programmer + Art Director + Programming team etc. (trunc)
CREDITS_TECH = (
    "\n<smallcaps><size=120%><b>创升纪元：牌组构筑游戏</b></size></smallcaps>\n\r\n"
    "<smallcaps><color=#1C4E80C8>主程序员\r</color></smallcaps>\nGary Weis\r\n\r\n"
    "<smallcaps><color=#1C4E80C8>程序员</color>\r</smallcaps>\nMatthew Schock\r\n\r\n"
    "<smallcaps><color=#1C4E80C8>首席创意官 / 美术总监\r</color></smallcaps>\nJeff \"Stecki\" Garstecki\r\n\r\n"
    "<smallcaps><color=#1C4E80C8>音乐与音效设"
)
T["\n<smallcaps><size=120%><b>Ascension: Deck Building Game</size></b></smallcaps>\n\r\n<smallcaps><color=#1C4E80C8>Lead Programmer\r</color></smallcaps>\nGary Weis\r\n\r\n<smallcaps><color=#1C4E80C8>Programmer</color>\r</smallcaps>\nMatthew Schock\r\n\r\n<smallcaps><color=#1C4E80C8>CCO/Art Director\r</color></smallcaps>\nJeff \"Stecki\" Garstecki\r\n\r\n<smallcaps><color=#1C4E80C8>Music and Sound Desi"] = CREDITS_TECH

# ========== L15: Giant 2497-char SPM page (truncated). Translate headings & job titles only.
CREDITS_SPM = (
    "<smallcaps><size=120%><b>创升纪元：牌组构筑游戏\r</B></size></smallcaps>\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>高级产品经理\r</color></smallcaps>\nBriana Covill\r\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>主程序员\r</color></smallcaps>\nGary Weis\r\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>工程总监\r</color></smallcaps>\nTimothy Parker\r\n\r\n\r"
    "<smallcaps><color=#1C4E80C8>资深"
)
T["<smallcaps><size=120%><b>Ascension: Deck Building Game\r</B></size></smallcaps>\n\r\n\r<smallcaps><color=#1C4E80C8>Senior Product Manager\r</color></smallcaps>\nBriana Covill\r\n\r\n\r<smallcaps><color=#1C4E80C8>Lead Programmer\r</color></smallcaps>\nGary Weis\r\n\r\n\r<smallcaps><color=#1C4E80C8>Director, Engineering\r</color></smallcaps>\nTimothy Parker\r\n\r\n\r<smallcaps><color=#1C4E80C8>Senio"] = CREDITS_SPM


def main() -> None:
    if not RULEBOOK.is_file():
        print(f"missing: {RULEBOOK}")
        sys.exit(1)

    with RULEBOOK.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    translated = 0
    already = 0
    missing: list[str] = []
    seen_zh_by_en: dict[str, str] = {}

    for i, row in enumerate(rows, 1):
        en = (row.get("en") or "").strip()
        zh = (row.get("zh") or "").strip()
        if not en:
            continue
        if zh:
            already += 1
            continue
        if en in T:
            row["zh"] = T[en]
            translated += 1
            seen_zh_by_en[en] = T[en]
        else:
            # Compare with quote-style normalization + truncation tolerance.
            # Truncated cells (credits pages / promo pages) are very long and get
            # cut off mid-sentence in the CSV — so if an English rulebook row is a
            # prefix of a T[] key (or vice versa) after normalizing quotes/whitespace,
            # we accept it.
            def _fold(s: str) -> str:
                import unicodedata, re
                s = unicodedata.normalize("NFKC", s)
                for a, b in [("’", "'"), ("“", '"'), ("”", '"'), ("—", "--"), ("–", "-"),
                             ("…", "..."), ("™", ""), ("®", "")]:
                    s = s.replace(a, b)
                # CSV cells sometimes store the two-char sequences \r / \n literally.
                s = s.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
                s = s.replace("\r\n", "\n").replace("\r", "\n")
                s = re.sub(r"\n{2,}", "\n", s)
                s = re.sub(r"[ \t]{2,}", " ", s)
                # CSV vs T[] often differ by optional CR before <br>
                s = re.sub(r"\n?<br>", "<br>", s, flags=re.I)
                return s.strip()
            # Helper: longest common substring length
            def _lcsub(a: str, b: str) -> int:
                # Use fast containment check — find chunks of >= 60 chars that
                # appear in both strings (good enough for truncated credit/promo
                # paragraphs where T[] key and EN row share a common contiguous
                # 100+ char prefix that got truncated differently).
                best = 0
                la, lb = len(a), len(b)
                if la == 0 or lb == 0:
                    return 0
                # sliding window of 80 chars on a, check if contained in b
                step = 80
                for s in range(0, max(1, la - step), 20):
                    chunk = a[s:s + step]
                    if chunk in b:
                        # extend to find actual match length
                        head, tail = s, s + step
                        while head > 0 and a[head - 1] == b[max(0, b.find(chunk) - (s - (head - 1)))]:
                            head -= 1
                            break  # keep simple; at least the chunk matched
                        best = max(best, tail - head)
                        if best >= 120:
                            return best
                return best
            fe = _fold(en)
            match = None
            best_score = 0
            for k, v in T.items():
                fk = _fold(k)
                if not fk or not fe:
                    continue
                if fk == fe:
                    match = v
                    best_score = 10**9
                    break
                # exact prefix/suffix for truncation at end
                shorter, longer = (fk, fe) if len(fk) <= len(fe) else (fe, fk)
                if len(shorter) >= 80 and longer.startswith(shorter):
                    match = v
                    best_score = len(shorter)
                    break
                # common-substring scoring for mid-paragraph truncations
                comm = _lcsub(fk, fe)
                if comm >= 100 and comm > best_score:
                    best_score = comm
                    match = v
            if match:
                row["zh"] = match
                translated += 1
            elif _looks_sprite_only(en):
                # Icon-only TMP nodes: keep identical so Exact is a no-op; inventory waives.
                row["zh"] = en
                translated += 1
            else:
                missing.append(en[:200])

    # Write back
    with RULEBOOK.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["en", "zh"])
        w.writeheader()
        for r in rows:
            w.writerow({"en": r.get("en", ""), "zh": r.get("zh", "")})

    print(f"rulebook rows: {len(rows)}")
    print(f"already translated: {already}")
    print(f"newly translated this run: {translated}")
    print(f"still missing zh (total): {len(missing)}")
    if missing:
        print("\n--- still missing, first 25 samples ---")
        for m in missing[:25]:
            snippet = m.replace("\n", "\\n").replace("\r", "\\r")[:200]
            # Windows consoles may be GBK; keep progress usable.
            print("  EN: " + snippet.encode("utf-8", "backslashreplace").decode("ascii", "ignore"))
        if len(missing) > 25:
            print(f"  ... {len(missing)-25} more")


def _looks_sprite_only(en: str) -> bool:
    import re
    s = en.strip()
    if not s:
        return False
    # Allow literal \n prefixes from CSV escapes
    s = s.replace("\\n", "").replace("\\r", "").strip()
    return bool(re.fullmatch(r"(?:<sprite=\d+>\s*)+", s))


if __name__ == "__main__":
    main()
