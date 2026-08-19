"""Build StreamingAssets overlay tables: loc-key and exact English -> Chinese."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from translate import strip_drop_cap  # noqa: E402

ZH = ROOT / "loc" / "zh-Hans"
EN_SHEETS = ROOT / "loc" / "en" / "sheets"
GLOSSARY = ROOT / "glossary" / "zh-Hans.csv"
OUT = ZH / "overlay.tsv"

TAG_RE = re.compile(r"</?(?:size|space|color|b|i|B|I|sprite)[^>]*>", re.I)
DROP_CAP_RE = re.compile(
    r"<size=\s*[^>]*>\s*(.)\s*</size>(?:<space=[^>]*>)?(.*)",
    re.I | re.S,
)


def load_pairs(path: Path, key_col: str, val_col: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {
            row[key_col]: row[val_col]
            for row in csv.DictReader(f)
            if row.get(key_col) and row.get(val_col)
        }


def load_two_col(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0] and row[0] not in {"key", "en"}:
                out[row[0]] = row[1]
    return out


def load_glossary() -> list[dict[str, str]]:
    if not GLOSSARY.is_file():
        return []
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        return [
            row
            for row in csv.DictReader(f)
            if (row.get("en") or "").strip()
            and not row["en"].strip().startswith("#")
            and (row.get("zh") or "").strip()
        ]


def strip_tags(text: str) -> str:
    text = strip_drop_cap(text)
    text = DROP_CAP_RE.sub(r"\1\2", text)
    text = TAG_RE.sub("", text)
    text = text.replace("<br>", "\n").replace("<BR>", "\n")
    return re.sub(r"\s+", " ", text).strip()


def drop_cap_variants(en: str) -> list[str]:
    """Gallery faction filters use TMP drop-cap markup."""
    if not en or not en[0].isalpha() or " " in en or "<" in en:
        return []
    first, rest = en[0], en[1:]
    variants = [f"<size=141%>{first}</size>{rest}"]
    if en == "Void":
        variants.append(f"<size=141%>{first}</size><space=-.15em>{rest}")
    return variants


SKIP_EXACT = {
    "Play",
    "Buy",
    "OK",
    "Ok",
    "Copy",
    "Use",
    "Give",
    "Target",
    "Select",
    "Defend",
    "Delete",
    "Reveal",
    "Discard",
    "View",
    "Join",
    "Start",
    "Back",
    "Close",
    "Done",
    "Yes",
    "No",
    # Confirm is a real dialog button label (end-turn etc.); do not skip.
    "Commit",
    "Dismiss",
    "Undo",
    "CLICK",
    "Click",
}

ALLOW_SHORT = {
    "Menu",
    "Exit",
    "VOID",
    "Void",
    "Offline",
    "Online",
    "Back",
    "Hero",
    "LOG",
    "Log",
    "Easy",
    "Hard",
    "Continue",
    "Cancel",
    "Confirm",
    "All",
    "Owned",
    "Fate",
    "FATE",
    "Echo",
    "ECHO",
    "Rune",
    "Deck",
    "Hand",
    "Day",
    "DAY",
    "Life",
    "Draw",
    "Name",
    "NAME",
    "Boons",
    "Rally",
    "Recur",
}


def put_exact(exact: dict[str, str], en: str, zh: str) -> None:
    if not en or not zh or en == zh:
        return
    if "${CLICK" in en or "${CLICK" in zh:
        return
    if "CLICK" in en.upper() and "CONTINUE" in en.upper():
        return

    def collapse(src: str) -> str:
        s = src.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
        while "  " in s:
            s = s.replace("  ", " ")
        s = re.sub(r" *\n *", "\n", s)
        while "\n\n\n" in s:
            s = s.replace("\n\n\n", "\n\n")
        return s.strip()

    def add(src: str) -> None:
        key = src.strip()
        if not key or key == zh:
            return
        if key in SKIP_EXACT:
            return
        if len(key) <= 4 and key not in ALLOW_SHORT and "<" not in key:
            return
        exact[src] = zh
        if key != src:
            exact[key] = zh
        collapsed = collapse(src)
        if collapsed and collapsed != src and collapsed != key:
            exact[collapsed] = zh

    add(en)
    stripped = strip_tags(en)
    if stripped and stripped != zh:
        add(stripped)
    plain = strip_drop_cap(en)
    if plain and plain != zh:
        add(plain)
    for variant in drop_cap_variants(en):
        add(variant)


def apply_glossary(exact: dict[str, str]) -> None:
    factions: dict[str, str] = {}
    types: dict[str, str] = {}
    for row in load_glossary():
        en = row["en"].strip()
        zh = row["zh"].strip()
        scope = (row.get("scope") or "").strip()
        put_exact(exact, en, zh)
        if scope == "faction":
            factions[en] = zh
        elif scope == "type":
            types[en] = zh
    for fen, fzh in factions.items():
        for ten, tzh in types.items():
            put_exact(exact, f"{fen} {ten}", fzh + tzh)
            put_exact(exact, f"{fen} {ten}s", fzh + tzh)
            # Gallery type line is "Event - Monster", not "Monster Event".
            put_exact(exact, f"{ten} - {fen}", f"{tzh} - {fzh}")
            put_exact(exact, f"{fen} - {ten}", f"{fzh} - {tzh}")


def expand_embedded(text: str, table: dict[str, str]) -> str:
    if not text or "${" not in text:
        return text
    cur = text
    for _ in range(4):
        nxt = re.sub(
            r"\$\{([^}]+)\}",
            lambda m: table.get(m.group(1), m.group(0)),
            cur,
        )
        if nxt == cur:
            return cur
        cur = nxt
    return cur


def alias_set_keys(keys: dict[str, str]) -> None:
    """Gallery loc uses CARDNAME_AVATAROFTHEFALLEN; the sheet often only has *10TH."""
    extras: dict[str, str] = {}
    for key, zh in keys.items():
        for suffix in ("10TH", "ETER"):
            if key.endswith(suffix):
                base = key[: -len(suffix)]
                if base and base not in keys:
                    extras[base] = zh
    keys.update(extras)


def apply_lua_card_exact(exact: dict[str, str]) -> None:
    path = ZH / "lua_cards.csv"
    if not path.is_file():
        return
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            en = (row.get("id") or "").strip()
            zh = (row.get("display_name") or "").strip()
            if en and zh and en != zh:
                put_exact(exact, en, zh)


def build_overlay() -> tuple[dict[str, str], dict[str, str]]:
    keys: dict[str, str] = {}
    exact: dict[str, str] = {}

    apply_glossary(exact)

    ui = load_pairs(ZH / "ui.csv", "key", "zh")
    keys.update(ui)

    cards = load_two_col(ZH / "cards.csv")
    keys.update(cards)
    packed = load_two_col(ZH / "cards_packed.csv")
    for key, zh in packed.items():
        keys.setdefault(key, zh)
    alias_set_keys(keys)

    tutorial = load_pairs(ZH / "tutorial.csv", "key", "zh")
    if not tutorial:
        tutorial = load_two_col(ZH / "tutorial.csv")
    for key, zh in tutorial.items():
        keys[key] = zh

    for sheet in ("Common_Strings.csv", "Common_Ingame.csv", "Ascension_Cards.csv"):
        en_map = load_two_col(EN_SHEETS / sheet)
        for key, en in en_map.items():
            zh = keys.get(key)
            if not zh:
                continue
            if key.startswith("Key_"):
                put_exact(exact, en, zh)
            elif key.startswith(("CARDNAME_", "EFFECT_", "FLAVOR_", "LABEL_")):
                if en.strip().startswith("<sprite"):
                    continue
                put_exact(exact, en, zh)
                if key.startswith("EFFECT_") and "${" in en:
                    put_exact(exact, expand_embedded(en, en_map), expand_embedded(zh, keys))

    apply_lua_card_exact(exact)

    combat = ZH / "combat_log.csv"
    if combat.is_file():
        with combat.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                put_exact(exact, row.get("en") or "", row.get("zh") or "")

    rulebook = ZH / "rulebook.csv"
    if rulebook.is_file():
        with rulebook.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                en = row.get("en") or ""
                zh = row.get("zh") or ""
                if not en or not zh or en == zh:
                    continue
                if en in {"ystic", "ultist"}:
                    continue
                put_exact(exact, en, zh)
                norm = row.get("norm") or ""
                if norm and norm != en:
                    put_exact(exact, norm, zh)

    runtime = ZH / "ui_runtime.csv"
    if runtime.is_file():
        with runtime.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                put_exact(exact, row.get("en") or "", row.get("zh") or "")

    achievements = ZH / "achievements.csv"
    if achievements.is_file():
        with achievements.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                put_exact(exact, row.get("en") or "", row.get("zh") or "")

    extras = {
        "Menu": "菜单",
        "Exit": "退出",
        "Offline": "离线",
        "Online": "在线",
        "Confirm": "确认",
        "App Store": "商店",
        "In-App Store": "商店",
        "内购店": "商店",
        "应用商店": "商店",
        "END TURN": "结束回合",
        "End Turn": "结束回合",
        "END\nTURN": "结束回合",
        "End\nTurn": "结束回合",
        "Continue": "继续",
        "CONTINUE": "继续",
        "Loading cards, please wait...": "正在加载卡牌，请稍候…",
        "Loading Cards, please wait...": "正在加载卡牌，请稍候…",
        "Loading cards, please wait": "正在加载卡牌，请稍候",
        "Loading rulebook,\nplease wait...": "正在加载规则书，\n请稍候…",
        "Loading rulebook, please wait...": "正在加载规则书，请稍候…",
        "Common": "普通",
        "Reward: Gain 1H.": "奖励：获得1荣誉。",
        "Reward: Gain 1 Honor.": "奖励：获得1荣誉。",
        "Reward: 1 Honor": "奖励：1荣誉",
        "The Cultist does not go to the void when defeated. You can defeat the Cultist any number of times each turn.": "邪教徒被击败后不会进入虚空区。每回合可以任意次数击败邪教徒。",
        "(The Cultist does not go to the void when defeated. You can defeat the Cultist any number of times each turn.)": "（邪教徒被击败后不会进入虚空区。每回合可以任意次数击败邪教徒。）",
        "Play Your Turn": "请出牌",
        "Stone Blade Newsletter Sign-Up": "订阅 Stone Blade 通讯",
        "Stone Blade Newsletter Sign-up": "订阅 Stone Blade 通讯",
        "STONE BLADE NEWSLETTER SIGN-UP": "订阅 Stone Blade 通讯",
        "STONE BLADE NEWSLETTER": "Stone Blade 通讯",
        "Subscribe to Stone Blade Newsletter": "订阅 Stone Blade 通讯",
        "Sign up to get the latest information and special deals direct to you.": "订阅即可获取最新资讯与优惠，直接发到你的邮箱。",
        "Cancel": "取消",
        "Owned": "已拥有",
        "Coming Soon": "即将推出",
        "Now Available": "现已推出",
        "Key Bindings": "按键绑定",
        "Play Card": "打出卡牌",
        "Magnify Card": "放大卡牌",
        "Scroll Magnified Card Left": "放大卡牌向左移",
        "Scroll Magnified Card Right": "放大卡牌向右移",
        "Show/Hide Pause Menu": "显示/隐藏暂停菜单",
        "Unmagnify Card & Close Card Trays": "取消放大并关闭卡牌托盘",
        "Play All Cards From Hand": "打出全部手牌",
        "End Your Turn": "结束回合",
        "Open/Close Construct Tray": "打开/关闭神器托盘",
        "Open/Close Discard Pile": "打开/关闭弃牌堆",
        "Open/Close Deck List": "打开/关闭牌库",
        "Open/Close Void List": "打开/关闭虚空区",
        "Open/Close Dreamborn List": "打开/关闭梦生列表",
        "Open/Close Renown Track": "打开/关闭声望轨道",
        "Downloadable Content": "可下载内容",
        "Promo 7": "特典 7",
        "Enlightened Monster": "圣贤怪物",
        "Lifebound Monster": "命约怪物",
        "Mechana Monster": "机械怪物",
        "Void Monster": "虚空怪物",
        "Common Monster": "普通怪物",
        "Event - Monster": "事件 - 怪物",
        "Event - Enlightened": "事件 - 圣贤",
        "Event - Lifebound": "事件 - 命约",
        "Event - Mechana": "事件 - 机械",
        "Event - Void": "事件 - 虚空",
        "Event - Common": "事件 - 普通",
        "Hero - Enlightened": "英雄 - 圣贤",
        "Hero - Lifebound": "英雄 - 命约",
        "Hero - Mechana": "英雄 - 机械",
        "Hero - Void": "英雄 - 虚空",
        "Hero - Monster": "英雄 - 怪物",
        "Construct - Enlightened": "神器 - 圣贤",
        "Construct - Lifebound": "神器 - 命约",
        "Construct - Mechana": "神器 - 机械",
        "Construct - Void": "神器 - 虚空",
        "Monster - Enlightened": "怪物 - 圣贤",
        "Monster - Lifebound": "怪物 - 命约",
        "Monster - Mechana": "怪物 - 机械",
        "Monster - Void": "怪物 - 虚空",
        "Monster - Common": "怪物 - 普通",
        "Treasure - Enlightened": "宝藏 - 圣贤",
        "Treasure - Lifebound": "宝藏 - 命约",
        "Treasure - Mechana": "宝藏 - 机械",
        "Treasure - Void": "宝藏 - 虚空",
        "Soul Gem - Enlightened": "灵魂宝石 - 圣贤",
        "Soul Gem - Lifebound": "灵魂宝石 - 命约",
        "Soul Gem - Mechana": "灵魂宝石 - 机械",
        "Soul Gem - Void": "灵魂宝石 - 虚空",
        "Offline Games": "离线对局",
        "Offline Game List": "离线对局列表",
        "Online Games": "在线对局",
        "Back": "返回",
        "LOG": "记录",
        "Log": "记录",
        "Music": "音乐",
        "Sound Effects": "音效",
        "Cultist Screams": "邪教徒惨叫",
        "PLAY ALL": "全部打出",
        "Play All": "全部打出",
        "Lobby": "大厅",
        "Version:": "版本：",
        "Settings": "设置",
        "Key Bindings": "按键绑定",
        "VOID": "虚空",
        "Void": "虚空",
        "Hero": "英雄",
        "Construct": "神器",
        "Monster": "怪物",
        "Enlightened": "圣贤",
        "Lifebound": "命约",
        "Mechana": "机械",
        "Enlightened Hero": "圣贤英雄",
        "Enlightened Construct": "圣贤神器",
        "Lifebound Hero": "命约英雄",
        "Lifebound Construct": "命约神器",
        "Mechana Hero": "机械英雄",
        "Mechana Construct": "机械神器",
        "Void Hero": "虚空英雄",
        "Void Construct": "虚空神器",
        "Always Available": "始终可用",
        "Always available": "始终可用",
        "Center Row": "中央牌列",
        "Honor": "荣誉",
        "Runes": "符文",
        "Power": "战力",
        "Deck": "牌库",
        "Discard": "弃牌堆",
        "Hand": "手牌",
        "Player": "玩家",
        "Settings": "设置",
        "Options": "选项",
        "Play Your Turn": "请出牌",
        "You May End Your Turn": "你可以结束回合",
        "You Must End Your Turn": "你必须结束回合",
        "Are you sure you want to end your turn?": "确定要结束你的回合吗？",
        "Not a valid target": "不是有效目标",
        "Confirm": "确认",
        "Confirm Revealed Cards": "确认已展示的卡牌",
        "Commit Your Decision": "确认你的决定",
        "Loading...": "加载中...",
        "Chronicle of the Godslayer": "弑神编年史",
        "Return of the Fallen": "邪神归来",
        "Storm of Souls": "灵魂风暴",
        "Immortal Heroes": "不朽英雄",
        "Rise of Vigil": "祈夜崛起",
        "Darkness Unleashed": "黑暗释放",
        "Realms Unraveled": "领域解开",
        "Dawn of Champions": "冠军黎明",
        "Dreamscape": "梦境",
        "War of Shadows": "暗影之战",
        "Gift of the Elements": "元素的馈赠",
        "Valley of the Ancients": "上古山谷",
        "Delirium": "谵妄",
        "Deliverance": "救赎",
        "Legends": "史诗传奇",
        "English": "英语",
        "French": "法语",
        "German": "德语",
        "Spanish": "西班牙语",
        "Italian": "意大利语",
        "Portuguese": "葡萄牙语",
        "Russian": "俄语",
        "Japanese": "日语",
        "Chinese": "中文",
        "Simplified Chinese": "简体中文",
        "Traditional Chinese": "繁体中文",
        "Easy": "简单",
        "Normal": "普通",
        "Hard": "困难",
        "Expert": "专家",
        "Beginner": "入门",
        "Honor Pool": "荣誉池",
        "Always available": "始终可用",
        "MULTI-UNITE": "多重联合",
        "Ongoing Trophy": "持续战利品",
        "Event Trophy": "事件战利品",
        "You can get a closer view of any card by right clicking it.  A left click will then return it to the play field so you can resume play.": "右键点击任意卡牌可查看大图。左键点击即可回到牌局继续游戏。",
        "You can get a closer view of any card by right clicking it. A left click will then return it to the play field so you can resume play.": "右键点击任意卡牌可查看大图。左键点击即可回到牌局继续游戏。",
        "You can get a closer view of any card by double tapping it.  A single tap will then return it to the play field so you can resume play.": "双击任意卡牌可查看大图。单击即可回到牌局继续游戏。",
    }
    for en, zh in extras.items():
        put_exact(exact, en, zh)

    for n in range(1, 21):
        put_exact(exact, f"Player {n}", f"玩家 {n}")
        put_exact(exact, f"Round {n}", f"第 {n} 回合")
        put_exact(exact, f"AI Player {n}", f"AI 玩家 {n}")

    return keys, exact


def escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def write_overlay(dest: Path | None = None) -> Path:
    keys, exact = build_overlay()
    dest = dest or OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# kind\tsrc\tzh"]
    for key, zh in sorted(keys.items()):
        lines.append(f"K\t{escape(key)}\t{escape(zh)}")
    for en, zh in sorted(exact.items(), key=lambda x: (-len(x[0]), x[0])):
        lines.append(f"E\t{escape(en)}\t{escape(zh)}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dest.name} ({len(keys)} keys, {len(exact)} exact)")
    return dest


def main() -> None:
    write_overlay()


if __name__ == "__main__":
    main()
