"""Fold BepInEx untranslated dumps into ui_runtime.csv / print missing loc keys.

Play the game once with the overlay enabled. The plugin writes unique English
strings to StreamingAssets/zh-cn/untranslated.tsv. Then:

    python tools/ingest_untranslated.py
    python tools/build_zh.py
    python tools/patch.py enable --locale zh-Hans
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


def main() -> None:
    path = dump_path()
    if not path.is_file():
        print(f"no dump yet: {path}")
        print("Launch the game, click through leftover English screens, then re-run.")
        return

    keys, exact = build_overlay()
    runtime = load_runtime()
    new_exact = 0
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
        if kind != "E":
            continue
        if src in exact or src in runtime or src in SKIP_EXACT:
            skipped += 1
            continue
        if src.startswith("${") or "<sprite" in src.lower():
            skipped += 1
            continue
        zh = translate_effect(src)
        if not zh or zh == src:
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

    print(f"already covered or skipped: {skipped}")
    print(f"missing loc keys: {len(missing_keys)}")
    for key, sample in missing_keys[:40]:
        extra = f"  {sample[:80]}" if sample else ""
        print(f"  {key}{extra}")
    if len(missing_keys) > 40:
        print(f"  ... {len(missing_keys) - 40} more")


if __name__ == "__main__":
    main()
