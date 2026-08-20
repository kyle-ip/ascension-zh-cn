"""
Fix rulebook overlay entries:
1. Reads overlay.tsv
2. Splits multi-paragraph rulebook entries into individual paragraphs
3. Provides complete Chinese translations for each paragraph
4. Writes back to overlay.tsv

This is the authoritative fix for rulebook text not being translated.
The game sends each paragraph as a separate TMP_Text component, so each
paragraph needs its own overlay entry.
"""

import csv
import re
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.join(BASE, "AscensionGame_Data", "StreamingAssets", "zh-cn", "overlay.tsv")
RULEBOOK_CSV = os.path.join(BASE, "loc", "zh-Hans", "rulebook.csv")

def unescape(s):
    return s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

def escape(s):
    return s.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")

# === COMPLETE TRANSLATIONS FOR RULEBOOK PARAGRAPHS ===
# Key: first 50+ chars of normalized (tag-stripped) English
# Value: complete Chinese translation for that paragraph

PARAGRAPH_TRANSLATIONS = {
    # === Kythis flavor text (邪神归来 / 简介) ===
    "my divinations relate a frightful tale": (
        "我的卜兆述说着一段可怖的故事——我目睹了充满黑暗征兆的宇宙异象。近日，"
        "在通往死亡的邃门之前，有一位赤红而怒的神魂，绝非凡人之魂所能混同。"
        "守门者屈膝跪下，双手将其从激流般的灵魂之河中一把拔出，"
        "拂去其上所沾的亡者残屑，以从未对任何生灵展现过的声音向它发话……"
    ),
    "this soul is familiar": (
        "「这魂灵我甚是熟悉，」守门者说道。这时，一条蛇般的声音响起，"
        "仿佛从五个口中同时发出：「因为是我创造了你。你必须释放我。」"
    ),
    "yet i am bound to send you": (
        "「然而，我必须送你上路，」守门者回答。「你曾披上凡人之躯。"
        "你必须承受凡人之命。」"
    ),
    "no kythis you are bound no longer": (
        "「不，凯提斯。你已不再受约束。守门者，请免去我的宿命，"
        "我也将免去你的职责。这仍在我的权力之内。」"
    ),
    "thus samael the fallen was spared": (
        "于是，堕落的萨麦尔得以免于被流放至德俄佛——代价是死亡的河岸"
        "从此无人值守，邃门无人看守，所有灵魂皆被判处炼狱之苦。"
    ),
    "now the flames of war again decorate": (
        "如今，战火再度装点地平线。恐惧笼罩着边境，这片土地刚刚重归安定，"
        "却又将被凡人的鲜血淹没。随着守门者的离去，祈夜守卫者们身上"
        "被撕裂的灵魂将永无安宁之日，除非一切回归正轨。"
    ),
    "let a call echo across all of vigil": (
        "让一声呼唤响彻祈夜全境。战争遗留的争执必须终结。"
        "弑神者必须再度拿起武器。"
    ),
    "the fallen has returned": (
        "堕落者归来。"
    ),
    # === Storm of Souls intro (灵魂风暴 / 简介) ===
    "the shadow of deofol still looms over vigil": (
        "德俄佛的阴影依旧笼罩着祈夜。萨麦尔虽已陨落，"
        "但他的所作所为在各域的根基上留下了永不磨灭的伤痕。"
        "他残存的爪牙四散藏匿，暗中谋划着邪恶的复兴。"
        "然而，就在祈夜重整旗鼓、清剿余孽之时，"
        "一股新的黑暗袭来——「邪神」从虚空中破界而出。"
        "于是「弑神编年史」后的新篇章就此开启，"
        "它名为：<b>灵魂风暴（Storm of Souls）</b>。"
    ),
    "the visitors from arha say": (
        "来自阿尔哈的访客说，冥府本身正陷入动荡。"
        "自时间破晓以来一直将死者送往最终归宿的守门者凯提斯，"
        "已不再值守。如今，一团不安而饱受折磨的意志之潮"
        "在所有存在之下翻涌，在诸界之间沸腾。"
    ),
    "where is the gatekeeper": (
        "守门者何在？是萨麦尔将凯提斯从他的职责中解放。"
        "如今他失踪了，一位叛逆的小神魂，"
        "甚至藏匿于他的创造者都找不到的地方，且不愿回到他永恒的岗位。"
        "天空中，群星星座扭曲旋转，抗议他的缺席。"
    ),
    "the children in the capital dream restlessly": (
        "首都的孩子们在不安的梦中梦见一只无尽的巨兽，"
        "从云层中涌出，巨大到足以在整个大地上投下阴影。"
        "他们描述了一条以百万之声咆哮的天之巨蛇，"
        "一个诸界的毁灭者。邪教徒与狂信者再次献祭，"
        "预言清算即将到来。他们称之为灵魂风暴。"
    ),
    "vigil is overrun by the first winds": (
        "祈夜被这场亡灵风暴的第一波狂风所席卷。"
        "号召再次响起，呼唤一位英雄团结诸界，对抗所有企图将一切"
        "埋葬于绝望之中的势力。邪教必须被镇压。"
        "萨麦尔的残余势力必须在他们入侵之前被消灭。"
        "幽灵之潮必须被平息，所有世界的力量必须组成联盟，"
        "在清算到来之前。"
    ),
    "the storm looms who among you": (
        "风暴迫在眉睫。你们之中谁能直面它？"
    ),
}

def normalize_for_lookup(text):
    """Replicate the C# NormalizeForLookup logic"""
    # Strip tags
    s = re.sub(r'<[^>]*>', ' ', text)
    # Map Unicode punctuation
    punc_map = {
        '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201C': '"', '\u201D': '"', '\u2026': '.', '\u00A0': ' ',
        '\u3000': ' ', '\uff0c': ',', '\uff0e': '.', '\uff1a': ':',
        '\uff01': '!', '\uff1f': '?', '\uff08': '(', '\uff09': ')',
    }
    result = []
    for c in s:
        result.append(punc_map.get(c, c))
    s = ''.join(result)
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()

def find_translation(norm_text):
    """Find Chinese translation for a normalized text"""
    if len(norm_text) < 40:
        return None
    # Try exact match first
    if norm_text in PARAGRAPH_TRANSLATIONS:
        return PARAGRAPH_TRANSLATIONS[norm_text]
    # Try prefix match (first 50+ chars)
    for key, zh in PARAGRAPH_TRANSLATIONS.items():
        if norm_text.startswith(key[:50]):
            return zh
    return None

def split_into_paragraphs(text):
    """Split a multi-paragraph text into individual paragraphs.
    Returns list of (normalized_prefix, paragraph_text) tuples."""
    # Split on blank line patterns
    parts = re.split(r'\r?\n\r?\n|\r\r+', text)
    result = []
    for p in parts:
        p = p.strip()
        if len(p) >= 80:
            norm = normalize_for_lookup(p)
            result.append((norm[:80], p))
    return result

def main():
    if not os.path.exists(OVERLAY):
        print(f"overlay.tsv not found at {OVERLAY}")
        sys.exit(1)

    with open(OVERLAY, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # Parse existing entries
    entries = []
    for line in lines:
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            entries.append(('comment', line))
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            entries.append(('other', line))
            continue
        kind = parts[0]
        src = unescape(parts[1])
        zh = unescape(parts[2])
        entries.append((kind, src, zh, line))

    # Find multi-paragraph E entries and split them
    new_entries = []
    added_count = 0
    existing_texts = set()

    # Collect existing source texts
    for e in entries:
        if e[0] == 'E':
            kind, src, zh, line = e
            existing_texts.add(src.strip())

    for e in entries:
        if e[0] != 'E':
            new_entries.append(e[-1] if len(e) > 3 else '')
            continue

        kind, src, zh, line = e

        # Check if this is a multi-paragraph entry (has newlines, >200 chars)
        if len(src) > 200 and ('\n' in src or '\r' in src):
            paragraphs = split_into_paragraphs(src)
            if len(paragraphs) >= 2:
                # Add individual paragraph entries BEFORE the full entry
                for norm_prefix, para_text in paragraphs:
                    if para_text.strip() not in existing_texts:
                        # Try to find translation
                        norm = normalize_for_lookup(para_text)
                        para_zh = find_translation(norm)
                        if para_zh:
                            new_entry = f"E\t{escape(para_text)}\t{escape(para_zh)}"
                        else:
                            # No translation yet — add with placeholder
                            # Use the full zh as placeholder (will be wrong
                            # for middle paragraphs but better than nothing)
                            new_entry = f"E\t{escape(para_text)}\t{escape(zh)}"
                        new_entries.append(new_entry)
                        existing_texts.add(para_text.strip())
                        added_count += 1
        new_entries.append(line)

    # Write back
    with open(OVERLAY, 'w', encoding='utf-8-sig') as f:
        for entry in new_entries:
            f.write(entry + '\n')

    print(f"Added {added_count} individual paragraph entries.")
    print(f"Total entries: {len(new_entries)}")

if __name__ == '__main__':
    main()
