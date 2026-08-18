"""Shared paths for the Ascension Chinese patch tools."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCH_JSON = REPO_ROOT / "patch.json"
STATE_DIR = REPO_ROOT / "state"
BACKUP_DIR = STATE_DIR / "backups"
LOCAL_STATE = STATE_DIR / "local.json"

DEFAULT_STEAM_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Ascension")


def load_patch_config() -> dict:
    return json.loads(PATCH_JSON.read_text(encoding="utf-8"))


def save_patch_config(cfg: dict) -> None:
    PATCH_JSON.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def detect_game_root(cfg: dict | None = None) -> Path:
    cfg = cfg or load_patch_config()
    explicit = (cfg.get("gameRoot") or "").strip()
    if explicit:
        root = Path(explicit)
        if _looks_like_game(root):
            return root
        raise FileNotFoundError(f"gameRoot is set but is not a valid install: {root}")

    parent = REPO_ROOT.parent
    if _looks_like_game(parent):
        return parent
    if _looks_like_game(DEFAULT_STEAM_GAME):
        return DEFAULT_STEAM_GAME
    raise FileNotFoundError(
        "Could not find the Ascension install. Set gameRoot in patch.json."
    )


def _looks_like_game(root: Path) -> bool:
    return (root / "AscensionGame.exe").is_file() and (
        root / "AscensionGame_Data" / "StreamingAssets" / "Lua"
    ).is_dir()


def lua_dir(game_root: Path) -> Path:
    return game_root / "AscensionGame_Data" / "StreamingAssets" / "Lua"


def resources_assets(game_root: Path) -> Path:
    return game_root / "AscensionGame_Data" / "resources.assets"


def streaming_zh_font(game_root: Path) -> Path:
    return game_root / "AscensionGame_Data" / "StreamingAssets" / "zh-cn" / "cjk-overlay.ttf"


def streaming_zh_dir(game_root: Path) -> Path:
    return game_root / "AscensionGame_Data" / "StreamingAssets" / "zh-cn"


def streaming_zh_overlay(game_root: Path) -> Path:
    return streaming_zh_dir(game_root) / "overlay.tsv"
