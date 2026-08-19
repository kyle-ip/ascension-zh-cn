# -*- coding: utf-8 -*-
"""Build loc/zh-Hans/rulebook_manual.json from need list + hand translations."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENS = ROOT / "loc" / "en" / "rulebook_need_zh_ens.json"
OUT = ROOT / "loc" / "zh-Hans" / "rulebook_manual.json"
LOG = ROOT / "loc" / "zh-Hans" / "rulebook_manual_log.txt"

# Exact EN -> ZH. Keys must match need file `en` character-for-character.
# Built by pairing below; missing keys are filled from TRANSLATIONS list order for hard rulebook items.


def n(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


TRANSLATIONS: dict[str, str] = {}


def add(en: str, zh: str) -> None:
    TRANSLATIONS[en] = zh
    TRANSLATIONS[n(en)] = zh


def seed() -> None:
    # --- Legends (ascl) ---
    add(
        "In this time of reckoning, Vigil calls forth a new generation of heroes. The untested must rise, guided by legends of old and the light of those who sacrificed before them. Against the Muses’ vision of unending chaos, the champions of today must forge their own legendary paths. The world awaits, and only through strength, courage, and unity can Vigil transcend this dark design. Your deeds are known, your valor witnessed, and through fire and flame, you must stand the test to become a legend—the future rests upon your ascension.",
        "在此清算之时，祈夜召唤新一代英雄。未经考验者必须挺身而出，以先贤传说与前人牺牲之光为指引。面对缪斯无尽混沌的异象，今日的勇士必须开辟属于自己的传奇之路。世界在等待——唯有凭力量、勇气与团结，祈夜才能超越这黑暗的设计。你的功绩人尽皆知，你的勇武有目共睹；历经烈火试炼，你必须成为传奇——未来系于你的登升。",
    )
    add(
        "As there is an element of divine inspiration in every act of creation, so too are there patrons for the arts of slaughter and destruction. For centuries, the Red Sisters have whispered their poisonous inspirations to the champions of destruction—Samael, Kythis, Xeron—fueling strife in the hearts of mortals and gods alike. They have watched as Vigil waged war after war, each act of defiance feeding their art of carnage. Now the Muses seek a final creation, one to remake Vigil from its very bones, a monument to the darkness they have nurtured across the ages.",
        "正如每一次创世都含有神启的火花，杀戮与毁灭的技艺也有其庇护者。数世纪以来，红姐妹向毁灭的勇士——萨麦尔、凯西斯、泽伦——低语有毒的灵感，在凡人与神明心中煽动纷争。她们注视祈夜一战再战，每一次反抗都滋养她们的屠戮艺术。如今缪斯寻求最终之作：从骨架重塑祈夜，为自己历经诸纪哺育的黑暗立起丰碑。",
    )
    add(
        "Eons have passed since Vigil’s heroes first defended their world against Samael, the Fallen God. Though the Godslayer’s victory brought peace, each hard-won era has been followed by threats even more harrowing. Vigil has birthed heroes to stand against every nightmare, but with each victory, darkness has gathered anew. Now, in the sulfurous depths of Deoful, something ancient stirs—the Red Sisters—the Muses of Malevolence. These shadowy patrons of slaughter and ruin stand poised to weave their own dreadful masterpiece.",
        "自祈夜英雄首次抵御堕落之神萨麦尔以来，已过去无数纪元。虽弑神者的胜利带来和平，每一段来之不易的时代之后，威胁却更加骇人。祈夜不断诞下英雄对抗每场梦魇，但每场胜利之后，黑暗又再度聚集。如今，在迪奥弗硫磺深处，古老之物苏醒——红姐妹，恶意缪斯。这些屠杀与毁灭的阴影庇护者，正准备编织她们可怖的杰作。",
    )
    add(
        "<margin-right=12em>Many cards in <i>Ascension: Legends™</i> have a Renown Threshold Effect—an extra ability that activates when you play the card, provided you’ve reached the required space on the Legendary Track for that faction.",
        "<margin-right=12em>《创升纪元：史诗传奇》中许多卡牌具有声望阈值效果——额外异能：当你打出该牌时，若你在该派系的传奇轨道上已到达所需格位，则触发该效果。",
    )
    add(
        "When you reach the 12th space on any faction’s path of the Legendary Track, you become a legend within that faction. From that turn onward, you may acquire or defeat 1 card from the Center Row belonging to that faction for free each turn. As with Boons, you can activate this ability at any time during your turn.",
        "当你在传奇轨道任一派系路径上到达第12格时，你成为该派系中的传奇。从该回合起，每回合你可以免费从中央牌列获取或击败1张属于该派系的卡牌。与恩赐一样，你可以在自己回合中的任何时候启动此能力。",
    )
    add(
        "Each Boon’s effect is written on its Legendary Character card and is unique to that Legend. When you earn a Boon, you may use it at any point during your turn before it ends. This allows you to keep acquiring Heroes and Constructs, advancing on the Legendary Track, or defeating Monsters before activating the Boon for maximum impact. However, unused Boons expire at the end of the turn.",
        "每份恩赐的效果写在其传奇角色卡上，且对该传奇独一无二。当你获得恩赐时，可在本回合结束前的任意时刻使用。这样你可以继续获取英雄与神器、在传奇轨道上推进，或击败怪物，再启动恩赐以发挥最大效果。未使用的恩赐会在回合结束时失效。",
    )
    add(
        "<margin-right=12em>In Ascension: Legends™, acquiring or defeating cards in the Center Row earns you Renown (<sprite=172>) with each faction shown on that card. Renown represents your rising status as a legend. Each point you gain moves you one space up the Legendary Track for the corresponding faction(s).",
        "<margin-right=12em>在《创升纪元：史诗传奇》中，获取或击败中央牌列的卡牌会为该牌所示的每个派系赢得声望（<sprite=172>）。声望代表你作为传奇的地位上升。你获得的每一点声望，会使你在对应派系的传奇轨道上前进一格。",
    )
    add(
        "<margin-right=13.5em>At the heart of Ascension: Legends™ is the Legendary Track, where you’ll compete to earn Renown (<sprite=172>) alongside some of the most iconic characters in the Ascension™ universe.<br><br>As you play, you’ll advance along this track, unlocking special abilities, known as Boons, granted by the Legends overseeing your game.<br><Br>Reach the end of the track, and you’ll secure your place as a legend within one of the four factions, gaining the ability to acquire or defeat a card of that faction for free at the start of each turn.",
        "<margin-right=13.5em>《创升纪元：史诗传奇》的核心是传奇轨道：你将与创升纪元宇宙中最具代表性的角色并肩，争夺声望（<sprite=172>）。<br><br>对局过程中，你会沿轨道前进，解锁由主持本局的传奇授予的特殊能力——恩赐。<br><Br>到达轨道尽头后，你将成为四派系之一中的传奇，并获得能力：每回合开始时免费获取或击败一张该派系卡牌。",
    )
    add(
        "Each Legendary Character comes from one of the four factions in Ascension™ and is loyal to that faction. To win their favor, you’ll need to show your allegiance by acquiring or defeating cards from their faction to earn Renown (<sprite=172>). Earn enough Renown with a faction, and you’ll unlock the Boon granted by that faction’s Legendary Character.",
        "每位传奇角色来自创升纪元四派系之一，并忠于该派系。要赢得其青睐，你需通过获取或击败其派系卡牌来展示效忠，从而获得声望（<sprite=172>）。在某一派系累积足够声望后，你将解锁该派系传奇角色授予的恩赐。",
    )
    add(
        "The threat posed by the Muses of Malevolence is one of the greatest Vigil has ever faced, but in its time of need, the champions of Vigil’s past have answered the call to battle. Former Heroes turned Legends, the Legendary Characters selected at the start of each game wait only for a worthy Hero to appear before lending their power to the struggle against the Red Sisters.",
        "恶意缪斯带来的威胁，是祈夜有史以来最严峻的之一；但在危难之时，往昔的勇士已应召参战。昔日英雄化作传奇——每局开始时选定的传奇角色，只待一位配得上的英雄出现，便会把力量借予对抗红姐妹的斗争。",
    )

    # --- Delirium ---
    add(
        Path("loc/en/rulebook_need_zh_ens.json").read_text(encoding="utf-8") and "",  # placeholder noop
        "",
    )


# Fix seed: remove broken add - rewrite seed properly without that hack
TRANSLATIONS.clear()


def main() -> None:
    # Load ens and apply translations from companion module body below via exec of pairs file
    pairs_path = ROOT / "loc" / "zh-Hans" / "_manual_pairs.json"
    if not pairs_path.is_file():
        raise SystemExit(f"missing {pairs_path}")
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    ens = json.loads(ENS.read_text(encoding="utf-8"))
    out = []
    skipped = []
    for i, item in enumerate(ens):
        en = item["en"]
        if en in {"ultist", "ystic"}:
            skipped.append(f"{i} drop-cap remnant {en}")
            continue
        if item["set"] == "runtime" and (
            "bundle" in en.lower()
            or "Promo" in en
            or "Game Design" in en
            or "smallcaps" in en.lower()
            and "Deck Building" in en
        ):
            skipped.append(f"{i} store/credits skipped")
            continue
        zh = pairs.get(en) or pairs.get(n(en))
        if not zh:
            # try by index key
            zh = pairs.get(str(i))
        if not zh:
            skipped.append(f"{i} NO TRANSLATION set={item['set']} len={len(en)}")
            continue
        out.append({"en": en, "zh": zh})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.write_text(
        f"translated {len(out)}\nskipped:\n" + "\n".join(skipped) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(out)}); skipped {len(skipped)}")


if __name__ == "__main__":
    main()
