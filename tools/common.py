"""Shared paths for the Ascension Chinese patch tools.

Game folder resolution (two modes only):
  1) config.json  — set \"gameRoot\" to the folder that contains AscensionGame.exe
  2) interactive  — if gameRoot is empty/invalid and prompt=True, ask once and write it back
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_JSON = REPO_ROOT / "config.json"
PATCH_JSON = REPO_ROOT / "patch.json"
STATE_DIR = REPO_ROOT / "state"
BACKUP_DIR = STATE_DIR / "backups"
LOCAL_STATE = STATE_DIR / "local.json"  # legacy; migrated into config.json if present


def load_patch_config() -> dict:
    return json.loads(PATCH_JSON.read_text(encoding="utf-8"))


def save_patch_config(cfg: dict) -> None:
    PATCH_JSON.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_user_config() -> dict:
    if not CONFIG_JSON.is_file():
        return {"gameRoot": ""}
    try:
        data = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"gameRoot": ""}
    if not isinstance(data, dict):
        return {"gameRoot": ""}
    data.setdefault("gameRoot", "")
    return data


def save_user_config(cfg: dict) -> None:
    out = {"gameRoot": (cfg.get("gameRoot") or "").strip()}
    CONFIG_JSON.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def save_game_root(root: Path) -> None:
    cfg = load_user_config()
    cfg["gameRoot"] = str(root.resolve())
    save_user_config(cfg)
    print(f"Saved gameRoot -> {CONFIG_JSON.name}")


def _looks_like_game(root: Path | None) -> bool:
    if root is None:
        return False
    try:
        return (root / "AscensionGame.exe").is_file() and (
            root / "AscensionGame_Data" / "StreamingAssets" / "Lua"
        ).is_dir()
    except OSError:
        return False


def _steam_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def add(path: Path | None) -> None:
        if path is None:
            return
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        roots.append(path)

    for env_name in ("STEAM_PATH", "SteamPath"):
        raw = (os.environ.get(env_name) or "").strip()
        if raw:
            add(Path(raw))

    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:
            winreg = None  # type: ignore
        if winreg is not None:
            for hive, subkey, value_names in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", ("SteamPath", "InstallPath")),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", ("InstallPath", "SteamPath")),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", ("InstallPath", "SteamPath")),
            ):
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        for name in value_names:
                            try:
                                val, _ = winreg.QueryValueEx(key, name)
                            except OSError:
                                continue
                            if isinstance(val, str) and val.strip():
                                add(Path(val.replace("/", "\\")))
                except OSError:
                    continue

    return roots


def _parse_library_folders(vdf_text: str) -> list[Path]:
    libs: list[Path] = []
    for match in re.finditer(r'"path"\s+"([^"]+)"', vdf_text):
        raw = match.group(1).replace("\\\\", "\\")
        libs.append(Path(raw))
    return libs


def _suggest_game_root() -> Path | None:
    """Optional default shown during interactive prompt (Enter to accept)."""
    parent = REPO_ROOT.parent
    if _looks_like_game(parent):
        return parent.resolve()

    seen: set[str] = set()
    for steam in _steam_roots():
        candidates = [steam / "steamapps" / "common" / "Ascension"]
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            for lib in _parse_library_folders(text):
                candidates.append(lib / "steamapps" / "common" / "Ascension")
        for candidate in candidates:
            try:
                key = str(candidate.resolve()).lower()
            except OSError:
                key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            if _looks_like_game(candidate):
                return candidate.resolve()
    return None


def _legacy_game_root() -> Path | None:
    """One-time migration from older locations into config.json."""
    for source in (PATCH_JSON, LOCAL_STATE):
        if not source.is_file():
            continue
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        raw = (data.get("gameRoot") or "").strip() if isinstance(data, dict) else ""
        if not raw:
            continue
        root = Path(raw).expanduser()
        if _looks_like_game(root):
            return root.resolve()
    return None


def _prompt_game_root() -> Path:
    suggestion = _suggest_game_root()
    print(f"{CONFIG_JSON.name}: gameRoot is empty.")
    print("Enter the folder that contains AscensionGame.exe")
    print("(paste a path, or drag the folder into this window).")
    if suggestion is not None:
        print(f"Suggested: {suggestion}")
        print("Press Enter to accept, or type another path:")
    else:
        print("Path:")

    while True:
        try:
            line = input("> ").strip().strip('"').strip("'")
        except EOFError as exc:
            raise FileNotFoundError(
                f"Set gameRoot in {CONFIG_JSON.name}, or re-run and enter the game folder."
            ) from exc

        if not line:
            if suggestion is not None:
                save_game_root(suggestion)
                return suggestion
            print("Path is empty; try again.")
            continue

        root = Path(line).expanduser()
        if _looks_like_game(root):
            root = root.resolve()
            save_game_root(root)
            return root
        print("Not a valid Ascension folder (need AscensionGame.exe + Lua). Try again.")


def detect_game_root(cfg: dict | None = None, *, prompt: bool = False) -> Path:
    """Resolve Ascension install: config.json first, else interactive (when prompt=True)."""
    del cfg  # gameRoot lives in config.json only

    user = load_user_config()
    explicit = (user.get("gameRoot") or "").strip()
    if explicit:
        root = Path(explicit).expanduser()
        if _looks_like_game(root):
            return root.resolve()
        print(f"{CONFIG_JSON.name} gameRoot is invalid: {root}")
        if not prompt:
            raise FileNotFoundError(
                f"Fix gameRoot in {CONFIG_JSON.name} (folder with AscensionGame.exe)."
            )

    legacy = _legacy_game_root()
    if legacy is not None:
        save_game_root(legacy)
        return legacy

    if prompt and sys.stdin.isatty():
        return _prompt_game_root()

    raise FileNotFoundError(
        f"Set gameRoot in {CONFIG_JSON.name}, or run .\\install.ps1 / .\\enable.ps1 to be prompted."
    )


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
