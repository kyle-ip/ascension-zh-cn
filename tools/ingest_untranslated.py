"""Fold BepInEx untranslated dumps into ui_runtime.csv / rulebook.csv.

Play the game once with the overlay enabled. The plugin writes unique English
strings to StreamingAssets/zh-cn/untranslated.tsv. Then:

    python tools/ingest_untranslated.py
    python tools/build_zh.py
    python tools/patch.py enable --locale zh-Hans

Kind legend:
  K = unseen LocalizationService keys (printed for manual mapping)
  E = short English UI strings (machine-translated via translate_effect)
  L = long English strings (rulebook body text, DLC store copy) — written
      to rulebook.csv with an empty `zh` column for manual translation.
      These contain rich-text tags (<br>, <b>, <smallcaps>, <sprite=N>)
      and exceed the 400-char limit on the E path.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root, streaming_zh_dir  # noqa: E402
from overlay import SKIP_EXACT, build_overlay  # noqa: E402
from translate import translate_effect  # noqa: E402

ZH = ROOT / "loc" / "zh-Hans"
RUNTIME = ZH / "ui_runtime.csv"
RULEBOOK = ZH / "rulebook.csv"


def unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def dump_path() -> Path:
    game = detect_game_root()
    return streaming_zh_dir(game) / "untranslated.tsv"


def load_runtime() -> dict[str, str]:
    if not RUNTIME.is_file():
        return {}
    with RUNTIME.open(encoding="utf-8", newline="") as f:
        return {row["en"]: row["zh"] for row in csv.DictReader(f) if row.get("en")}


def load_rulebook() -> dict[str, str]:
    if not RULEBOOK.is_file():
        return {}
    with RULEBOOK.open(encoding="utf-8", newline="") as f:
        return {row["en"]: row.get("zh") or "" for row in csv.DictReader(f) if row.get("en")}


def looks_rulebook_body(src: str) -> bool:
    """Rulebook and DLC store paragraphs must NOT be routed through
    ``translate_effect`` (card-effect word-replacement pipeline).  That
    pipeline produces the "符文为一的两main resources在Ascension" style
    garbage visible on the rulebook screenshot.

    Heuristics (any one = route to rulebook.csv with empty zh for manual
    translation):

      * Length > 200 characters — typical for a single rulebook paragraph.
      * Presence of rulebook-only formatting tags: <allcaps>, <smallcaps>,
        <indent=...>, <margin=...>, <br> that are not seen on regular cards.
      * Presence of rulebook-only section markers as prefix or standalone:
        "Resources:", "RUNES:", "POWER:", "HONOR:", "FACTIONS:",
        "FATE CARDS:", "What's New", "Features", "Introduction",
        "Additional IP Development", "Temples:", "Honor Pool:",
        "Description:", "Promo Cards Included:",
        "Unique new cards per set:", "Includes ", "<allcaps>RESOURCES</allcaps>"
      * Strings that already contain "<sprite=" (card icons) AND are longer
        than 80 chars (Pasythea cost / DLC promo paragraphs fall here).
      * Lexical markers: "For millennia, the world of Vigil", "the player
        who gains the most Honor Points", "in Ascension" (appears 2+ times)
    """
    if len(src) > 200:
        return True
    lower = src.lower()
    if any(t in lower for t in ("<allcaps", "<indent=", "<margin=", "<smallcaps")):
        return True
    # Rulebook section headings markers (case-sensitive)
    SECTION_MARKERS = (
        "Resources:", "RUNES:", "POWER:", "HONOR:", "FACTIONS:",
        "FATE CARDS:", "What's New", "Features", "Introduction",
        "Additional IP Development", "Temples:", "Honor Pool:",
        "Description:", "Promo Cards Included:",
        "Unique new cards per set:", "RESOURCES",
    )
    if any(m in src for m in SECTION_MARKERS):
        return True
    # "Includes NN unique new cards" (DLC box footer) variants
    if "Includes " in src and ("unique new cards" in lower or "unique<br>new cards" in lower):
        return True
    # Rulebook lore / common phrases
    if "For millennia, the world of Vigil" in src:
        return True
    if "the player who gains the most Honor Points" in src:
        return True
    if "Ascension" in src and lower.count("in ascension") >= 1 and len(src) > 80:
        return True
    if "<sprite" in lower and len(src) > 80:
        return True
    return False


def main() -> None:
    path = dump_path()
    if not path.is_file():
        print(f"no dump yet: {path}")
        print("Launch the game, click through leftover English screens, then re-run.")
        return

    keys, exact = build_overlay()
    runtime = load_runtime()
    rulebook = load_rulebook()
    new_exact = 0
    new_long = 0
    new_rulebook_short = 0
    missing_keys: list[tuple[str, str]] = []
    skipped = 0

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        kind, src = parts[0], unescape(parts[1])
        sample = unescape(parts[2]) if len(parts) > 2 else ""
        if kind == "K":
            if src in keys:
                continue
            missing_keys.append((src, sample))
            continue
        if kind == "L":
            # Long-string path: rulebook body + DLC store copy. Skip
            # template strings; preserve everything else (including
            # rich-text tags). Leave `zh` empty for manual translation.
            if src in exact or src in rulebook:
                skipped += 1
                continue
            if src.startswith("${"):
                skipped += 1
                continue
            rulebook[src] = ""
            new_long += 1
            continue
        if kind != "E":
            continue
        if src in exact or src in runtime or src in SKIP_EXACT:
            skipped += 1
            continue
        if src.startswith("${"):
            skipped += 1
            continue
        # ======= ROUTE RULEBOOK PARAGRAPHS OUT OF translate_effect() ======
        # Do NOT use the card-effect word-replacement pipeline on rulebook
        # narrative or DLC store paragraphs.  Write them to rulebook.csv
        # with an empty zh column just like kind 'L', so a human can craft a
        # full-sentence translation.
        if looks_rulebook_body(src):
            if src in exact or src in rulebook:
                skipped += 1
                continue
            # Skip obvious developer placeholders even if markers match.
            if "Confirmation Popup Text Here" in src:
                skipped += 1
                continue
            rulebook[src] = ""
            new_rulebook_short += 1
            continue
        # Skip pure <sprite> tag rows (icon glyphs that carry no text).
        if "<sprite" in src.lower() and len(src.strip()) < 80:
            skipped += 1
            continue
        zh = translate_effect(src)
        if not zh or zh == src:
            skipped += 1
            continue
        # DropCap polish_copy may leave the zh equal to src on edge cases.
        if zh.strip() == src.strip():
            skipped += 1
            continue
        runtime[src] = zh
        new_exact += 1

    if new_exact:
        with RUNTIME.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["en", "zh"])
            w.writeheader()
            for en, zh in runtime.items():
                w.writerow({"en": en, "zh": zh})
        print(f"appended {new_exact} strings -> {RUNTIME.name} (total {len(runtime)})")
    else:
        print("no new exact UI strings to ingest")

    if new_long:
        with RULEBOOK.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["en", "zh"])
            w.writeheader()
            for en, zh in rulebook.items():
                w.writerow({"en": en, "zh": zh})
        print(f"appended {new_long} long strings -> {RULEBOOK.name} (total {len(rulebook)}, {sum(1 for v in rulebook.values() if v)} already translated)")
    else:
        print("no new long strings to ingest")

    print(f"already covered or skipped: {skipped}")
    print(f"missing loc keys: {len(missing_keys)}")
    for key, sample in missing_keys[:40]:
        extra = f"  {sample[:80]}" if sample else ""
        print(f"  {key}{extra}")
    if len(missing_keys) > 40:
        print(f"  ... {len(missing_keys) - 40} more")


if __name__ == "__main__":
    main()
