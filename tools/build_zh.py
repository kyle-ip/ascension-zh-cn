"""Rebuild loc/zh-Hans string tables from English extracts."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from translate import translate_effect, translate_flavor, translate_label, translate_name  # noqa: E402

GLOSSARY = ROOT / "glossary" / "terms.csv"
OVERRIDES = ROOT / "loc" / "zh-Hans" / "overrides.csv"
EN_CARDS = ROOT / "loc" / "en" / "lua_cards.csv"
EN_UI = ROOT / "loc" / "en" / "ui.csv"
EN_TUTORIAL = ROOT / "loc" / "en" / "tutorial.csv"
EN_TUTORIAL_DESKTOP = ROOT / "loc" / "en" / "tutorial_desktop.csv"
EN_CARDS_RAW = ROOT / "loc" / "en" / "cards_en_raw.csv"
OUT_DIR = ROOT / "loc" / "zh-Hans"


def load_overrides() -> dict[str, dict[str, str]]:
    with OVERRIDES.open(encoding="utf-8", newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def variant_base(card_id: str) -> str:
    return re.sub(r" (10TH|SoS|RoV|RU)$", "", card_id)


def build_lua_cards(overrides: dict[str, dict[str, str]]) -> None:
    rows = []
    with EN_CARDS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ov = overrides.get(row["id"]) or dict(overrides.get(variant_base(row["id"]), {}))
            if ov and row["id"] not in overrides and ov.get("source"):
                ov["source"] = ov["source"] + "+variant"
            display = (ov.get("display_name") if ov else "") or translate_name(row["display_name"])
            effect = (ov.get("effect_text") if ov else "") or translate_effect(row["effect_text"])
            flavor = (ov.get("flavor_text") if ov else "") or translate_flavor(row.get("flavor_text") or "")
            source = (ov.get("source") if ov else "") or "machine"
            rows.append(
                {
                    "id": row["id"],
                    "card_set": row.get("card_set", ""),
                    "display_name": display,
                    "effect_text": effect,
                    "flavor_text": flavor,
                    "source": source,
                }
            )
    out = OUT_DIR / "lua_cards.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "card_set", "display_name", "effect_text", "flavor_text", "source"],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.name} ({len(rows)} cards)")


def _translate_card_key(
    key: str,
    value: str,
    name_by_norm: dict[str, str],
    effect_by_norm: dict[str, str],
) -> str:
    if key.startswith("LABEL_"):
        return translate_label(value)
    if key.startswith("CARDNAME_"):
        norm = key[len("CARDNAME_") :]
        return name_by_norm.get(norm) or translate_name(value)
    if key.startswith("EFFECT_") or key.startswith(
        ("FATE_", "TROPHY_", "ENERGY_", "DAY_", "NIGHT_")
    ):
        prefix = key.split("_", 1)[0] + "_"
        norm = key[len(prefix) :]
        return effect_by_norm.get(norm) or translate_effect(value)
    if key.startswith("FLAVOR_"):
        return translate_flavor(value)
    return translate_effect(value)


def _load_card_en_rows() -> list[tuple[str, str]]:
    """Prefer the runtime loc sheet; packed cards_EN is a stale subset."""
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    sheet = ROOT / "loc" / "en" / "sheets" / "Ascension_Cards.csv"
    if sheet.is_file():
        with sheet.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                key = (row.get("key") or "").strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                ordered.append((key, row.get("en") or ""))
    if EN_CARDS_RAW.is_file():
        with EN_CARDS_RAW.open(encoding="utf-8", newline="") as f:
            for parts in csv.reader(f):
                if not parts:
                    continue
                key = parts[0]
                if not key or key in seen or key in {"key", "en"}:
                    continue
                seen.add(key)
                ordered.append((key, parts[1] if len(parts) > 1 else ""))
    return ordered


def build_cards_en_csv(overrides: dict[str, dict[str, str]]) -> None:
    """Translate runtime CARDNAME_*/EFFECT_* keys for the overlay."""
    name_by_norm = {}
    effect_by_norm = {}
    for row in overrides.values():
        key = re.sub(r"[^A-Z0-9]", "", row["id"].upper())
        if row.get("display_name"):
            name_by_norm[key] = row["display_name"]
        if row.get("effect_text"):
            effect_by_norm[key] = row["effect_text"]

    out_rows: list[tuple[str, str]] = []
    for key, value in _load_card_en_rows():
        zh = _translate_card_key(key, value, name_by_norm, effect_by_norm)
        out_rows.append((key, zh))

    out = OUT_DIR / "cards.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerows(out_rows)
    print(f"wrote {out.name} ({len(out_rows)} rows)")

    raw_keys: set[str] = set()
    if EN_CARDS_RAW.is_file():
        with EN_CARDS_RAW.open(encoding="utf-8", newline="") as f:
            for parts in csv.reader(f):
                if parts and parts[0] not in {"key", "en"}:
                    raw_keys.add(parts[0])
    packed = [(k, v) for k, v in out_rows if k in raw_keys]
    packed_path = OUT_DIR / "cards_packed.csv"
    with packed_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerows(packed)
    print(f"wrote {packed_path.name} ({len(packed)} rows, cards_EN sized)")


def build_ui() -> None:
    skip_prefix = ("Key_Hint_",)
    leaked_markers = ("${ICON_", "<size=", "LABEL_")
    rows = []
    extra = {}
    ui_override = OUT_DIR / "ui.csv"
    if ui_override.is_file():
        with ui_override.open(encoding="utf-8", newline="") as f:
            extra = {r["key"]: r["zh"] for r in csv.DictReader(f) if r.get("key")}

    auto = []
    with EN_UI.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key, en = row["key"], row["en"]
            if key.startswith(skip_prefix):
                continue
            if any(m in en for m in leaked_markers):
                continue
            zh = extra.get(key) or translate_effect(en)
            # short menu words
            simple = {
                "Play": "开始",
                "Settings": "设置",
                "Menu": "菜单",
                "Login": "登录",
                "Exit": "退出",
                "Cancel": "取消",
                "Confirm": "确认",
                "Continue": "继续",
                "Back": "返回",
                "Close": "关闭",
                "Start": "开始",
                "Finish": "完成",
                "Done": "完成",
                "Empty": "空",
                "None": "无",
                "Human": "人类",
                "Fast": "快",
                "Slow": "慢",
                "Medium": "中",
                "Pause": "暂停",
                "Resume": "继续",
                "Tutorial": "教程",
                "Friends": "好友",
                "Profile": "档案",
                "Options": "选项",
                "Warning": "警告",
                "Error": "错误",
                "Loading": "加载中",
                "Waiting": "等待中",
                "Online": "在线",
                "Offline": "离线",
                "Invite": "邀请",
                "Reject": "拒绝",
                "Join": "加入",
                "Delete": "删除",
                "Purchase": "购买",
                "Purchased": "已购买",
                "Locked": "已锁定",
                "Rating": "评分",
                "Round": "回合",
                "Turn": "回合",
                "Hour": "小时",
                "Hours": "小时",
                "Minute": "分钟",
                "Minutes": "分钟",
                "Second": "秒",
                "Seconds": "秒",
                "Monday": "星期一",
                "Tuesday": "星期二",
                "Wednesday": "星期三",
                "Thursday": "星期四",
                "Friday": "星期五",
                "Saturday": "星期六",
                "Sunday": "星期日",
                "Mon": "一",
                "Tues": "二",
                "Wed": "三",
                "Thurs": "四",
                "Fri": "五",
                "Sat": "六",
                "Sun": "日",
            }
            if en in simple:
                zh = simple[en]
            auto.append({"key": key, "en": en, "zh": extra.get(key, zh)})

    out = OUT_DIR / "ui.full.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "en", "zh"])
        w.writeheader()
        w.writerows(auto)
    print(f"wrote {out.name} ({len(auto)} keys)")


def _load_tutorial_en() -> list[tuple[str, str]]:
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in (EN_TUTORIAL, EN_TUTORIAL_DESKTOP):
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if not row or row[0] == "key":
                    continue
                key, en = row[0], row[1] if len(row) > 1 else ""
                if not key or key in seen:
                    continue
                seen.add(key)
                ordered.append((key, en))
    return ordered


def _polish_tutorial_zh(zh: str) -> str:
    return (
        zh.replace("创升纪元（暗杀神）", "创升纪元")
        .replace("（暗杀神）", "")
        .replace("暗杀神", "")
    )


def build_tutorial() -> None:
    existing = {}
    path = OUT_DIR / "tutorial.csv"
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0] != "key":
                    existing[row[0]] = row[1]
    rows = []
    used: set[str] = set()
    for key, en in _load_tutorial_en():
        if existing.get(key):
            rows.append((key, _polish_tutorial_zh(existing[key])))
            used.add(key)
            continue
        zh = translate_effect(en)
        zh = zh.replace("Ascension", "创升纪元")
        for en_name, zh_name in (
            ("Apprentices", "学徒"),
            ("Apprentice", "学徒"),
            ("Militia", "民兵"),
            ("Mystic", "秘教士"),
            ("Cultist", "邪教徒"),
            ("Snapdragon", "金鱼草"),
            ("Wolf Shaman", "狼萨满"),
            ("Arha Initiate", "亚哈新兵"),
            ("Heavy Infantry", "重装步兵"),
            ("Demon Slayer", "恶魔杀手"),
            ("Master Dhartha", "达萨大师"),
            ("Shadow Star", "暗影之星"),
            ("Wind Tyrant", "风之暴君"),
            ("Muramasa", "村正"),
            ("Emri, One with the Void", "与虚空合一的艾姆瑞"),
            ("Emri", "艾姆瑞"),
            ("Samael's Trickster", "萨麦尔的诡术师"),
            ("Druids of the Stone Circle", "石环德鲁伊"),
            ("Mistake of Creation", "造物之误"),
            ("Runes", "符文"),
            ("Rune", "符文"),
            ("Power", "战力"),
            ("Honor", "荣誉"),
            ("Heroes", "英雄"),
            ("Hero", "英雄"),
            ("Constructs", "神器"),
            ("Construct", "神器"),
            ("Monsters", "怪物"),
            ("Monster", "怪物"),
            ("Void", "虚空区"),
            ("Center Row", "中央牌列"),
            ("discard pile", "弃牌堆"),
            ("Discard Pile", "弃牌堆"),
        ):
            zh = zh.replace(en_name, zh_name)
        rows.append((key, _polish_tutorial_zh(zh)))
        used.add(key)
    for key, zh in existing.items():
        if key not in used:
            rows.append((key, _polish_tutorial_zh(zh)))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["key", "zh"])
        writer.writerows(rows)
    asset = OUT_DIR / "tutorial_asset.csv"
    with asset.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerows(rows)
    print(f"wrote tutorial.csv and tutorial_asset.csv ({len(rows)} lines)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overrides = load_overrides()
    build_lua_cards(overrides)
    build_cards_en_csv(overrides)
    build_ui()
    build_tutorial()
    from overlay import write_overlay  # noqa: E402

    write_overlay()


if __name__ == "__main__":
    main()
