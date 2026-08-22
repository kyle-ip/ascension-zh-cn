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

# Paragraph separator patterns in rulebook/DLC text.
# The CSV uses escaped "\r" and "\n" (literal backslash + letter) as well as
# actual control characters to separate paragraphs. Also handle <br><br>
# for DLC store text.
_PARA_SPLIT_RE = re.compile(
    r"<br>\s*<br>|</br>\s*</br>"  # HTML line breaks
    r"|\\r\\n|\\n|\\r"              # Escaped \r\n, \n, \r (literal backslash sequences)
    r"|\r\n|\r|\n",                 # Actual CR, LF, CRLF control characters
    re.I
)

# DLC bundle text patterns (contain <br> tags and bundle keywords)
_DLC_PATTERNS = re.compile(
    r"(favorite fan bundle|this bundle|promo cards included)",
    re.I
)

def _split_rulebook_paragraphs(text: str) -> list[str]:
    """Split a multi-paragraph rulebook/DLC text into individual paragraphs.

    The game renders each paragraph as a separate TMP_Text component.
    Returns only paragraphs with >= 80 characters (short ones are likely
    headers or formatting artifacts).
    """
    if not text or "<br>" not in text and "\n" not in text and "\r" not in text:
        return [text] if text else []
    parts = _PARA_SPLIT_RE.split(text)
    result = []
    for p in parts:
        p = p.strip()
        if len(p) >= 80:
            result.append(p)
    return result if len(result) >= 2 else [text] if text else []


def _split_chinese_for_paragraphs(zh: str, en_paragraphs: list[str]) -> list[str]:
    """Best-effort split of Chinese translation to match English paragraphs.

    For rulebook text, the Chinese is often a complete translation that
    doesn't have 1:1 paragraph correspondence. This function:
    1. If Chinese is also multi-paragraph (separated by \n), split similarly
    2. Otherwise, return empty strings for unmatched paragraphs
       (caller should handle the missing translations)
    """
    # Check if Chinese has paragraph separators too
    if "\n" in zh or "\r" in zh:
        zh_parts = _PARA_SPLIT_RE.split(zh)
        zh_parts = [p.strip() for p in zh_parts if p.strip()]
        if len(zh_parts) == len(en_paragraphs):
            return zh_parts
    # Fallback: return empty strings — caller should skip these
    return [""] * len(en_paragraphs)


def _is_dlc_bundle_text(text: str) -> bool:
    """Check if text looks like a DLC store bundle description."""
    return bool(_DLC_PATTERNS.search(text) and "<br>" in text)


# Individual paragraph translations for rulebook text.
# Key: normalized (tag-stripped, lowercased) prefix of the English paragraph
# Value: complete Chinese translation for that paragraph
#
# These are used when rulebook.csv entries are multi-paragraph but the
# Chinese translation doesn't have 1:1 paragraph correspondence.
_RULEBOOK_PARAGRAPH_TRANSLATIONS: dict[str, str] = {}

def _init_paragraph_translations() -> None:
    """Lazily populate the paragraph translation dictionary.

    Keys are normalized (tag-stripped, lowercased, collapsed whitespace)
    prefixes of English paragraphs. Values are full Chinese translations.
    """
    if _RULEBOOK_PARAGRAPH_TRANSLATIONS:
        return
    entries = [
        # === Kythis flavor text (邪神归来 / 简介) ===
        # P1: Opening tale
        (
            "my divinations relate a frightful tale- i have seen cosmic events of the darkest portent",
            "我的卜兆述说着一段可怖的故事——我目睹了充满黑暗征兆的宇宙异象。近日，在通往死亡的邃门之前，"
            "有一位赤红而怒的神魂，绝非凡人之魂所能混同。守门者屈膝跪下，双手将其从激流般的灵魂之河中一把拔出，"
            "拂去其上所沾的亡者残屑，以从未对任何生灵展现过的声音向它发话……"
        ),
        # P2: Gatekeeper recognizes the soul
        (
            '"this soul is familiar," said the gatekeeper',
            "「这魂灵我甚是熟悉，」守门者说道。这时，一条蛇般的声音响起，仿佛从五个口中同时发出："
            "「因为是我创造了你。你必须释放我。」"
        ),
        # P3: Gatekeeper's duty
        (
            '"yet, i am bound to send you on your way," the gatekeeper replied',
            "「然而，我必须送你上路，」守门者回答。「你曾披上凡人之躯。你必须承受凡人之命。」"
        ),
        # P4: Samael's argument (in italics)
        (
            "no, kythis. you are bound no longer. forbear my fate, gatekeeper",
            "「不，凯提斯。你已不再受约束。守门者，请免去我的宿命，我也将免去你的职责。这仍在我的权力之内。」"
        ),
        # P5: Samael spared, consequences
        (
            "thus, samael the fallen was spared exile to deofol",
            "于是，堕落的萨麦尔得以免于被流放至德俄佛——代价是死亡的河岸从此无人值守，"
            "邃门无人看守，所有灵魂皆被判处炼狱之苦。"
        ),
        # P6: War returns
        (
            "now, the flames of war again decorate the horizon",
            "如今，战火再度装点地平线。恐惧笼罩着边境，这片土地刚刚重归安定，"
            "却又将被凡人的鲜血淹没。随着守门者的离去，祈夜守卫者们身上被撕裂的灵魂将永无安宁之日，"
            "除非一切回归正轨。"
        ),
        # P7: Call to arms
        (
            "let a call echo across all of vigil",
            "让一声呼唤响彻祈夜全境。战争遗留的争执必须终结。"
            "弑神者必须再度拿起武器。"
        ),
        # P8: Closing
        (
            "the fallen has returned",
            "堕落者归来。"
        ),

        # === Storm of Souls intro (灵魂风暴 / 简介) ===
        # P1: Deofol's shadow
        (
            "the shadow of deofol still looms over vigil",
            "德俄佛的阴影依旧笼罩着祈夜。萨麦尔虽已陨落，但他的所作所为在各域的根基上留下了永不磨灭的伤痕。"
            "他残存的爪牙四散藏匿，暗中谋划着邪恶的复兴。然而，就在祈夜重整旗鼓、清剿余孽之时，"
            "一股新的黑暗袭来——「邪神」从虚空中破界而出。于是「弑神编年史」后的新篇章就此开启，"
            "它名为：<b>灵魂风暴（Storm of Souls）</b>。"
        ),
        # P2: Afterlife in turmoil
        (
            "the visitors from arha say that the afterlife itself is in turmoil",
            "来自阿尔哈的访客说，冥府本身正陷入动荡。自时间破晓以来一直将死者送往最终归宿的守门者凯提斯，"
            "已不再值守。如今，一团不安而饱受折磨的意志之潮在所有存在之下翻涌，在诸界之间沸腾。"
        ),
        # P3: Gatekeeper missing
        (
            "where is the gatekeeper? it was samael that freed kythis",
            "守门者何在？是萨麦尔将凯提斯从他的职责中解放。如今他失踪了，一位叛逆的小神魂，"
            "甚至藏匿于他的创造者都找不到的地方，且不愿回到他永恒的岗位。天空中，群星星座扭曲旋转，"
            "抗议他的缺席。"
        ),
        # P4: Children's dreams
        (
            "the children in the capital dream restlessly of an endless beast",
            "首都的孩子们在不安的梦中梦见一只无尽的巨兽，从云层中涌出，巨大到足以在整个大地上投下阴影。"
            "他们描述了一条以百万之声咆哮的天之巨蛇，一个诸界的毁灭者。邪教徒与狂信者再次献祭，"
            "预言清算即将到来。他们称之为灵魂风暴。"
        ),
        # P5: Vigil overrun
        (
            "vigil is overrun by the first winds of this coming storm",
            "祈夜被这场亡灵风暴的第一波狂风所席卷。号召再次响起，呼唤一位英雄团结诸界，"
            "对抗所有企图将一切埋葬于绝望之中的势力。邪教必须被镇压。萨麦尔的残余势力"
            "必须在他们入侵之前被消灭。幽灵之潮必须被平息，所有世界的力量必须组成联盟，"
            "在清算到来之前。"
        ),
        # P6: Storm looms
        (
            "the storm looms. who among you will stand before it",
            "风暴迫在眉睫。你们之中谁能直面它？"
        ),

        # === Core game rules (end game / play order) ===
        # End game condition
        (
            "the game ends when a certain amount of honor has been earned, depending on the number of players",
            "当累计获得的荣誉达到某个阈值时游戏结束，阈值取决于玩家人数。"
        ),
        (
            "cards in each player's deck are also worth honor points",
            "玩家牌组中的卡牌同样提供荣誉点数，每张卡牌的数值标注在卡牌右下角。"
        ),
        (
            "if multiple players have the same number of honor points",
            "若多名玩家的荣誉点数相同，则最后达成该点数的玩家获胜（即结算时牌堆顶部最后一张的持有者）。"
        ),
        # Play order
        (
            "1. play cards from your hand to gain runes, power, and honor",
            "1. 打出手中的卡牌以获取符文、战力和荣誉。获取英雄与神器，或将怪物击败放入弃牌堆。"
        ),
        (
            "2. after you are done acquiring heroes and constructs and defeating monsters",
            "2. 当你完成获取英雄、神器和击败怪物后，将场上所有剩余的卡牌放入弃牌堆。"
        ),
        (
            "3. you are dealt five cards from your personal deck to replenish your hand",
            "3. 从个人牌堆抽五张牌补充手牌。若牌堆抽空，则洗弃牌堆形成新牌堆后继续抽牌。"
        ),
        # CotG intro (game setup)
        (
            "for millennia, the world of vigil has been isolated and protected from other realms",
            "千百年来，<b>祈夜</b>世界一直与其他领域隔绝并受其庇护。如今，次元之间的屏障正在崩塌，"
            "<b>堕落之神萨麦尔</b>率领他的怪物大军从异界归来！"
        ),
        (
            "you are one of the few warriors capable of facing this threat",
            "你是少数能够直面此威胁、守护你世界的战士之一，但你无法孤军奋战！"
            "你必须召唤强大的英雄与神器助你作战。"
        ),
        (
            "the player who gains the most honor points will lead his army",
            "赢得最多<b>荣誉点数</b>的玩家将率领自己的军队击败<b>堕落者</b>，夺得<b>弑神者</b>的称号。"
        ),
    ]
    for prefix, zh in entries:
        _RULEBOOK_PARAGRAPH_TRANSLATIONS[prefix] = zh


def _lookup_paragraph_translation(en_text: str) -> str | None:
    """Look up a pre-built translation for a rulebook paragraph.

    Args:
        en_text: The English paragraph text (with tags)

    Returns:
        Chinese translation if found, None otherwise
    """
    _init_paragraph_translations()
    # Normalize: strip tags, lowercase, collapse whitespace
    norm = re.sub(r"<[^>]*>", " ", en_text)
    norm = re.sub(r"\s+", " ", norm).strip().lower()
    # Try prefix match (first 50+ chars)
    for prefix, zh in _RULEBOOK_PARAGRAPH_TRANSLATIONS.items():
        if norm.startswith(prefix):
            return zh
    return None


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
    """Load authoritative hand-edited glossary.

    The glossary is the SINGLE SOURCE OF TRUTH for exact string mappings.
    ``glossary_gen.py`` can rebuild it (merge seed rows and derive the
    coverage report) without touching hand-edited translations.  Only
    rows with status != "approved" are filtered out here.
    """
    if not GLOSSARY.is_file():
        return []
    with GLOSSARY.open(encoding="utf-8", newline="") as f:
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(f):
            en = (row.get("en") or "").strip()
            zh = (row.get("zh") or "").strip()
            if not en or not zh or en.startswith("#"):
                continue
            status = (row.get("status") or "approved").strip() or "approved"
            if status != "approved":
                continue
            row["en"] = en
            row["zh"] = zh
            row["scope"] = (row.get("scope") or "").strip()
            rows.append(row)
        return rows


def derive_glossary_exact() -> tuple[dict[str, str], set[str]]:
    """Return (glossary_exact_map, allow_short_set) from the authoritative
    glossary.  ``allow_short_set`` auto-includes every approved entry with
    len(en) <= 4 — manual ALLOW_SHORT is gone.
    """
    exact: dict[str, str] = {}
    allow_short: set[str] = set()
    factions: dict[str, str] = {}
    types: dict[str, str] = {}
    for row in load_glossary():
        en = row["en"]
        zh = row["zh"]
        scope = row["scope"]
        if en == zh:
            continue
        exact[en] = zh
        if len(en) <= 4:
            allow_short.add(en)
        if scope == "faction":
            factions[en] = zh
        elif scope == "type":
            types[en] = zh
        # Case-variant exact aliases for short UI labels/headings.  merge_seed
        # deduplicates by (en.casefold, scope), so the glossary file only
        # stores one representative — but runtime exact matching is case-
        # sensitive, so we synthesize common variants here.  This covers:
        #   Reward: ↔ REWARD: ↔ reward:    (card-face labels)
        #   Player Name ↔ PLAYER NAME      (login form)
        #   Start ↔ START ↔ start          (button text)
        #   Promo Pack #1 ↔ PROMO PACK #1  (shop list)
        # We deliberately skip scope={phrase,card,credits,world,series,
        # faction,type,promo,chapter,resource} because case matters there.
        if scope in {"label", "login", "button", "shop", "ui"}:
            variants_to_try: list[str] = []
            if " " not in en:
                # single-word: titlecase + upper + lower
                variants_to_try += [en.upper(), en.lower(), en.title()]
            else:
                # multi-word: ALLCAPS, alllower, each-word-capitalized
                variants_to_try += [en.upper(), en.lower(),
                                    " ".join(w.capitalize() for w in en.split())]
            seen: set[str] = {en}
            for alt in variants_to_try:
                if alt in seen:
                    continue
                seen.add(alt)
                if alt not in exact:
                    exact[alt] = zh
                    # Short variants also bypass the length filter.
                    if len(alt) <= 4:
                        allow_short.add(alt)
    # Faction × Type combinators (Enlightened Hero → 圣贤英雄) — only add
    # when not already covered by hand-edited rows.
    for fen, fzh in factions.items():
        for ten, tzh in types.items():
            for suf in ("", "s"):
                k = f"{fen} {ten}{suf}"
                if k not in exact:
                    exact[k] = fzh + tzh
    return exact, allow_short


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


# ---------------------------------------------------------------------------
# Blacklist — ONLY used to protect tutorial click-prompts from being
# translated (Plugin.cs has a parallel guard that skips tutorial prompts so
# the game's own state machine still matches the English CLICK* tokens).
# NEVER put UI buttons (Confirm / Start / Close / Yes / No / Undo ...) here:
# those come from the glossary and MUST be visible as Chinese on screen.
# ---------------------------------------------------------------------------
SKIP_EXACT = {
    "CLICK",
    "Click",   # CLICK_CONTINUE etc.
    "View",    # tutorial-only "View card" hint that matches state machine
    "Join",    # tutorial "Join the fight" style prompts; keep until verified
}

# =========================================================================
# LEGACY — ALLOW_SHORT was hand-written before glossary became the source
# of truth.  It is still used as a SAFETY NET:
#
#   (1) for any len<=4 string that is NOT yet in the glossary, the entries
#       below still let it pass through put_exact() so we don't silently
#       drop rare code abbreviations (CotG / RotF / 10th / IH / ...).
#
#   (2) derive_glossary_exact() auto-extracts the len<=4 APPROVED glossary
#       rows and adds them to a runtime set that put_exact merges in.
#
# If you add a new short label (e.g. "FAQ", "Bid", "SBT"), prefer adding it
# to the glossary (scope=button, status=approved) rather than extending
# this list.  Then glossary_gen.py report will track coverage.
# =========================================================================
_ALLOW_SHORT_LEGACY = {
    "CotG", "10th", "RotF", "SoS", "IH", "RoV", "DU", "RU", "DoC",
    "DS", "WoS", "GotE", "VotA", "DLV", "DLRM", "LGS",
    "On", "Off", "Medium", "Fast", "Slow",
    "LOG", "Log",
    "VOID", "Offline", "Online", "Continue", "Cancel", "Owned",
    # set abbreviations not reachable via glossary yet (these are seen in
    # theme-selection thumbnails):
    "10th",  # duplicates above kept for safety
}


def put_exact(exact: dict[str, str], en: str, zh: str, *,
              allow_short: set[str] | None = None,
              overwrite: bool = False) -> None:
    """Insert an exact (en -> zh) mapping plus 3 variant forms.

    Short strings (len <= 4) are only inserted if the en is present in
    ``allow_short`` (which comes from the glossary + legacy safety net).

    ``overwrite`` semantics:
      * False (default)  — preserve existing entries so the first layer
        (glossary) wins.  Used for ui.csv reverse-maps, cards.csv,
        ui_runtime.csv, rulebook.csv, combat_log.csv.
      * True             — replace if present.  Used ONLY for extras (the
        legacy last-resort dict), where we occasionally want to override
        a glossary entry with a markup-aware variant.
    """
    if not en or not zh or en == zh:
        return
    # CSV cells often store literal \r / \n as two-char sequences. Normalize
    # before indexing so overlay Exact keys match game TMP text.
    en = (
        en.replace("\\r\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\n", "\n")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    zh = (
        zh.replace("\\r\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\n", "\n")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    if not en or not zh or en == zh:
        return
    if "${CLICK" in en or "${CLICK" in zh:
        return
    if "CLICK" in en.upper() and "CONTINUE" in en.upper():
        return
    allow = _ALLOW_SHORT_LEGACY if allow_short is None else (allow_short | _ALLOW_SHORT_LEGACY)

    def add(src: str) -> None:
        key = src.strip()
        if not key or key == zh:
            return
        if key in SKIP_EXACT:
            return
        if len(key) <= 4 and key not in allow and "<" not in key:
            return
        # Respect overwrite semantics.  We write both src and its stripped
        # version independently (in case they differ).
        if overwrite or src not in exact:
            exact[src] = zh
        if key != src and (overwrite or key not in exact):
            exact[key] = zh

    add(en)
    stripped = strip_tags(en)
    if stripped and stripped != zh:
        add(stripped)
    plain = strip_drop_cap(en)
    if plain and plain != zh:
        add(plain)
    for variant in drop_cap_variants(en):
        add(variant)


def apply_glossary(exact: dict[str, str], *, allow_short: set[str]) -> None:
    """Dump glossary-derived exact pairs into ``exact`` via put_exact().

    ``put_exact`` re-runs the same variant pipeline (tags stripped / drop-cap
    variants / plain) used for all other sources, so the plugin always sees
    the same 4 forms regardless of whether a string came from the glossary,
    extras, ui_runtime.csv, or rulebook.csv.
    """
    factions: dict[str, str] = {}
    types: dict[str, str] = {}
    for row in load_glossary():
        en = row["en"]
        zh = row["zh"]
        scope = row["scope"]
        put_exact(exact, en, zh, allow_short=allow_short)
        if scope == "faction":
            factions[en] = zh
        elif scope == "type":
            types[en] = zh
    for fen, fzh in factions.items():
        for ten, tzh in types.items():
            put_exact(exact, f"{fen} {ten}", fzh + tzh, allow_short=allow_short)
            put_exact(exact, f"{fen} {ten}s", fzh + tzh, allow_short=allow_short)


def build_overlay() -> tuple[dict[str, str], dict[str, str]]:
    keys: dict[str, str] = {}
    exact: dict[str, str] = {}

    # 1) Glossary is SINGLE SOURCE OF TRUTH — load it first so later layers
    #    can override individual strings but UI buttons / login / shop /
    #    rulebook chapter headings / faction / resource / verb labels are
    #    always driven by the hand-editable glossary CSV.
    glossary_exact, glossary_short = derive_glossary_exact()
    for en, zh in glossary_exact.items():
        put_exact(exact, en, zh, allow_short=glossary_short)
    apply_glossary(exact, allow_short=glossary_short)

    cards = load_two_col(ZH / "cards.csv")
    keys.update(cards)

    # NB: ui.csv after cards.csv so hand-curated ui flavor overrides (e.g.
    # FLAVOR_NAIRIHENGEQUEEN narrative) win over glossary-generated zh in
    # cards.csv for the same FLAVOR_* key.
    ui = load_pairs(ZH / "ui.csv", "key", "zh")
    keys.update(ui)

    tutorial = load_pairs(ZH / "tutorial.csv", "key", "zh")
    if not tutorial:
        tutorial = load_two_col(ZH / "tutorial.csv")
    for key, zh in tutorial.items():
        keys[key] = zh

    for sheet in ("Common_Strings.csv", "Common_Ingame.csv", "Ascension_Cards.csv"):
        en_map = load_two_col(EN_SHEETS / sheet)
        for key, en in en_map.items():
            zh = keys.get(key)
            if zh and key.startswith("Key_"):
                put_exact(exact, en, zh, allow_short=glossary_short)

    # Card name/effect exact maps cause a second TMP layer on top of
    # LocalizationService text. Harmony GetTextByKey owns those strings.

    combat = ZH / "combat_log.csv"
    if combat.is_file():
        with combat.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                put_exact(exact, row.get("en") or "", row.get("zh") or "",
                          allow_short=glossary_short)

    runtime = ZH / "ui_runtime.csv"
    if runtime.is_file():
        with runtime.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                put_exact(exact, row.get("en") or "", row.get("zh") or "",
                          allow_short=glossary_short)

    # Rulebook body text + DLC store copy (kind 'L' in untranslated.tsv).
    # These strings carry rich-text tags (<br>, <b>, <smallcaps>, <sprite=N>);
    # put_exact also adds the stripped-tag variant so the plugin's Rewrite
    # finds them via Exact lookup or the NormalizeUi path.
    #
    # IMPORTANT: The game renders each paragraph as a SEPARATE TMP_Text
    # component, so multi-paragraph entries must be split into individual
    # paragraphs to be matched correctly. Individual paragraph translations
    # are looked up via _lookup_paragraph_translation().
    rulebook = ZH / "rulebook.csv"
    if rulebook.is_file():
        with rulebook.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                en = row.get("en") or ""
                zh = row.get("zh") or ""
                if not en or not zh:
                    continue
                # Split multi-paragraph entries into individual paragraphs
                # so each can be matched by the plugin's per-TMP_Text lookup.
                paragraphs = _split_rulebook_paragraphs(en)
                if len(paragraphs) >= 2:
                    # Try to find individual translations for each paragraph
                    for para_en in paragraphs:
                        para_zh = _lookup_paragraph_translation(para_en)
                        if para_zh:
                            put_exact(exact, para_en, para_zh, allow_short=glossary_short)
                # Also keep the original full entry for cases where the game
                # sends the complete text as one block (e.g., credits).
                put_exact(exact, en, zh, allow_short=glossary_short)

    # Also split DLC store entries from ui_runtime if they're multi-paragraph
    runtime = ZH / "ui_runtime.csv"
    if runtime.is_file():
        with runtime.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                en = row.get("en") or ""
                zh = row.get("zh") or ""
                if not en or not zh:
                    continue
                if _is_dlc_bundle_text(en):
                    paragraphs = _split_rulebook_paragraphs(en)
                    if len(paragraphs) >= 2:
                        zh_paragraphs = _split_chinese_for_paragraphs(zh, paragraphs)
                        for para_en, para_zh in zip(paragraphs, zh_paragraphs):
                            if para_en and para_zh and para_en != para_zh:
                                put_exact(exact, para_en, para_zh, allow_short=glossary_short)

    # extras = legacy one-off strings.  Glossary is the preferred home for
    # new entries; extras is kept for duplicates / rich-text variants /
    # numerical Player-n templating / phrases with unusual markup.
    # Strings already in the glossary are skipped here to avoid two copies.
    extras = {
        "END TURN": "结束回合",
        "End Turn": "结束回合",
        "END\nTURN": "结束回合",
        "End\nTurn": "结束回合",
        "CONTINUE": "继续",
        "Loading cards, please wait...": "正在加载卡牌，请稍候…",
        "Loading Cards, please wait...": "正在加载卡牌，请稍候…",
        "Loading cards, please wait": "正在加载卡牌，请稍候",
        "Reward: Gain 1H.": "奖励：获得1荣誉。",
        "Reward: Gain 1 Honor.": "奖励：获得1荣誉。",
        "Reward: 1 Honor": "奖励：1荣誉",
        "The Cultist does not go to the void when defeated. You can defeat the Cultist any number of times each turn.": "邪教徒被击败后不会进入虚空区。每回合可以任意次数击败邪教徒。",
        "(The Cultist does not go to the void when defeated. You can defeat the Cultist any number of times each turn.)": "（邪教徒被击败后不会进入虚空区。每回合可以任意次数击败邪教徒。）",
        "You May End Your Turn": "你可以结束回合",
        "You Must End Your Turn": "你必须结束回合",
        "Are you sure you want to end your turn?": "确定要结束你的回合吗？",
        "Not a valid target": "不是有效目标",
        "Confirm Revealed Cards": "确认已展示的卡牌",
        "Commit Your Decision": "确认你的决定",
        "Loading...": "加载中...",
        "Version:": "版本：",
        "Key Bindings": "按键绑定",
        "French": "法语",
        "German": "德语",
        "Spanish": "西班牙语",
        "Italian": "意大利语",
        "Portuguese": "葡萄牙语",
        "Russian": "俄语",
        "Japanese": "日语",
        "MULTI-UNITE": "多重联合",
        "Ongoing Trophy": "持续战利品",
        "Event Trophy": "事件战利品",
        "You can get a closer view of any card by right clicking it.  A left click will then return it to the play field so you can resume play.": "右键点击任意卡牌可查看大图。左键点击即可回到牌局继续游戏。",
        "You can get a closer view of any card by right clicking it. A left click will then return it to the play field so you can resume play.": "右键点击任意卡牌可查看大图。左键点击即可回到牌局继续游戏。",
        "You can get a closer view of any card by double tapping it.  A single tap will then return it to the play field so you can resume play.": "双击任意卡牌可查看大图。单击即可回到牌局继续游戏。",
        # ======= 缺失翻译补充 =======
        # 离线对局 - 空存档提示
        'No saved games found.\\nSelect "Create Game"\\nto start a new game.\\n': "暂无保存的对局。\\n选择「创建对局」\\n开始新游戏。\\n",
        # 选项 - 标题、主题缩略、速度、分析
        "Theme": "主题",
        "Theme Selection": "主题选择",
        "Game Speed": "游戏速度",
        "Animation Speed": "动画速度",
        "Analytics": "分析",
        "Share Analytics": "分享分析数据",
        "Gameplay Analytics": "游戏分析",
        "Resolution": "分辨率",
        "Fullscreen": "全屏",
        "Windowed": "窗口",
        "Windowed Mode": "窗口模式",
        # 按键绑定
        "Play Card": "出牌",
        "Magnify Card": "放大卡牌",
        "Scroll Magnified Card Left": "放大卡左翻",
        "Scroll Magnified Card Right": "放大卡右翻",
        "Show/Hide Pause Menu": "显示/隐藏暂停菜单",
        "Unmagnify Card & Close Card Trays": "缩小并关闭卡列表",
        "Play All Cards From Hand": "打出全部手牌",
        "End Your Turn": "结束回合",
        "Open/Close Construct Tray": "打开/关闭神器栏",
        "Open/Close Discard Pile": "打开/关闭弃牌堆",
        "Open/Close Deck List": "打开/关闭牌库列表",
        "Open/Close Void List": "打开/关闭虚空列表",
        "Open/Close Dreamborn List": "打开/关闭梦生列表",
        "Open/Close Renown Track": "打开/关闭名望轨道",
        "L Mouse": "鼠标左键",
        "R Mouse": "鼠标右键",
        "LeftArrow": "← 方向键左",
        "RightArrow": "→ 方向键右",
        "Escape": "Esc 键",
        "Space": "空格键",
        # 成就 / 图鉴
        "Achievements": "成就",
        "Collection": "收藏",
        # 主菜单/其它标题 尾部空格变体
        "Achievements ": "成就",
        "Gallery ": "图鉴",
        "Options ": "选项",
        "Key Bindings ": "按键绑定",
        "Create ": "创建",
        "Offline Games ": "离线对局",
        # 分析数据弹窗说明
        "Share your gameplay analytics with Playdek to help improve Ascension? This can be changed anytime in the Options Menu.": "向 Playdek 分享你的游戏分析数据以帮助改进《创升纪元》？此选项可随时在选项菜单中修改。",
        "Share your gameplay analytics with Playdek to help improve Ascension? This can be changed anytime in the Options Menu": "向 Playdek 分享你的游戏分析数据以帮助改进《创升纪元》？此选项可随时在选项菜单中修改",
        # 带 <smallcaps><size> 标题装饰变体（put_exact 会用 strip_tags 做纯文本版本）
        "<smallcaps><size=120%>O</size></smallcaps>ffline<smallcaps><size=120%>G</size></smallcaps>ames": "离线对局",
        "<smallcaps><size=120%>K</size></smallcaps>ey<smallcaps><size=120%>B</size></smallcaps>indings": "按键绑定",
        "<smallcaps><size=120%>O</size></smallcaps>ptions": "选项",
        "<smallcaps><size=120%>A</size></smallcaps>chievements": "成就",
        "<smallcaps><size=120%>G</size></smallcaps>allery": "图鉴",
        # Newsletter signup (Playdek)
        "Stone Blade Newsletter Sign-Up": "订阅 Stone Blade 通讯",
        "Stone Blade Newsletter Sign-up": "订阅 Stone Blade 通讯",
        "STONE BLADE NEWSLETTER SIGN-UP": "订阅 Stone Blade 通讯",
        "STONE BLADE NEWSLETTER": "Stone Blade 通讯",
        "Subscribe to Stone Blade Newsletter": "订阅 Stone Blade 通讯",
        "Sign up to get the latest information and special deals direct to you.": "订阅即可获取最新资讯与优惠，直接发到你的邮箱。",
        # Monster faction combos (already covered by glossary but keep as
        # defensive duplicates).
        "Enlightened Monster": "圣贤怪物",
        "Lifebound Monster": "命约怪物",
        "Mechana Monster": "机械怪物",
        "Void Monster": "虚空怪物",
        "Common Monster": "普通怪物",
        "Offline Game List": "离线对局列表",
        "Online Games": "在线对局",
    }
    for en, zh in extras.items():
        if en in glossary_exact:  # glossary owns the canonical translation
            continue
        # extras is legacy last-resort: still don't overwrite glossary, but
        # DO overwrite any reverse-map copy we added from ui.csv (those came
        # from a "Key_" match, not a deliberate glossary decision).  So we
        # keep overwrite=False here — the glossary layer always wins.
        put_exact(exact, en, zh, allow_short=glossary_short)

    for n in range(1, 21):
        put_exact(exact, f"Player {n}", f"玩家 {n}", allow_short=glossary_short)
        put_exact(exact, f"Round {n}", f"第 {n} 回合", allow_short=glossary_short)
        put_exact(exact, f"AI Player {n}", f"AI 玩家 {n}", allow_short=glossary_short)

    return keys, exact


def escape(value: str) -> str:
    """Serialize a string for overlay.tsv (single-escaped controls).

    CSV cells often store the two-character sequences ``\\r`` / ``\\n`` literally.
    Normalize those (and real CR/LF) to real newlines *before* escaping, otherwise
    we double-escape to ``\\\\r`` and the plugin can never Exact-match game text.
    """
    if not value:
        return ""
    value = (
        value.replace("\\r\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\n", "\n")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")


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
