"""Same-size replacements of hardcoded TMP strings in Unity scene files.

Title-screen hex buttons live in level1, not in the loc JSON sheets.
Only replace length-prefixed exact strings so names like OfflineGames stay intact.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from common import BACKUP_DIR, detect_game_root

# (english, chinese) — UTF-8 lengths must match.
TITLE_REPLACEMENTS = (
    ("Offline", "离线 "),
    ("Online", "在线"),
    ("In-App Store", "应用商店"),
    ("App Store", "内购店"),
    ("Stone Blade Newsletter Sign-Up", "订阅 Stone Blade 通讯     "),
    ("Stone Blade Newsletter Sign-up", "订阅 Stone Blade 通讯     "),
    (
        "Sign up to get the latest information and special deals direct to you.",
        "订阅即可获取最新资讯与优惠，直接发到你的邮箱。 ",
    ),
    ("Cancel", "取消"),
)


def _level1(game_root: Path) -> Path:
    return game_root / "AscensionGame_Data" / "level1"


def backup_level1(game_root: Path) -> Path:
    src = _level1(game_root)
    dest = BACKUP_DIR / "level1"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"backed up {src.name} -> {dest}")
    return dest


def restore_level1(game_root: Path) -> None:
    src = BACKUP_DIR / "level1"
    if not src.is_file():
        print("no level1 backup; skip scene restore")
        return
    shutil.copy2(src, _level1(game_root))
    print(f"restored {src} -> level1")


def _prefixed(text: str) -> bytes:
    raw = text.encode("utf-8")
    return len(raw).to_bytes(4, "little") + raw


def apply_scene_strings(game_root: Path | None = None) -> int:
    game_root = game_root or detect_game_root()
    backup_level1(game_root)
    path = _level1(game_root)
    shutil.copy2(BACKUP_DIR / "level1", path)
    data = bytearray(path.read_bytes())
    patched = 0
    for en, zh in TITLE_REPLACEMENTS:
        old = _prefixed(en)
        new = _prefixed(zh)
        if len(new) != len(old):
            print(f"skip scene {en!r}: {len(new)} != {len(old)} bytes")
            continue
        count = data.count(old)
        if count == 0:
            print(f"scene string not found: {en}")
            continue
        data = data.replace(old, new)
        patched += count
        print(f"scene {en!r} -> zh ({count} hit(s))")
    path.write_bytes(data)
    print(f"wrote {path} ({patched} scene strings)")
    return patched
