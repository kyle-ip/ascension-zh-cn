"""Enable or disable the external Chinese overlay on the local install."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import (  # noqa: E402
    BACKUP_DIR,
    detect_game_root,
    load_patch_config,
    lua_dir,
    save_patch_config,
    streaming_zh_dir,
    streaming_zh_font,
    streaming_zh_overlay,
)
from assets import apply_loc_json, apply_textassets, restore_assets  # noqa: E402
from bepinex import disable_runtime, enable_runtime  # noqa: E402
from fonts import collect_charset, subset_font  # noqa: E402
from scene import apply_scene_strings, restore_level1  # noqa: E402

LOCALE_DIR = {
    "zh-Hans": ROOT / "loc" / "zh-Hans",
    "zh-Hant": ROOT / "loc" / "zh-Hant",
}


def _lua_escape(value: str) -> str:
    value = (
        value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
    )
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _load_card_map(locale: str) -> dict[str, dict[str, str]]:
    path = LOCALE_DIR[locale] / "lua_cards.csv"
    mapping = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            mapping[row["id"]] = row
    return mapping


def _load_messages(locale: str) -> dict[str, str]:
    path = LOCALE_DIR[locale] / "combat_log.csv"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {row["en"]: row["zh"] for row in csv.DictReader(f) if row.get("en")}


def _replace_field(body: str, field: str, new_value: str) -> str:
    if not new_value:
        return body
    escaped = '"' + _lua_escape(new_value) + '"'
    # Match a single quoted string *or* several joined with `..`. The single-
    # quote pattern must not run first: it would leave leftover English pieces.
    pattern = re.compile(
        rf'({field}\s*=\s*)(?:"(?:\\.|[^"\\])*"(?:\s*\.\.\s*)?)+'
    )

    def replacer(match: re.Match[str]) -> str:
        return match.group(1) + escaped

    if pattern.search(body):
        return pattern.sub(replacer, body, count=1)
    insert = f'\n   {field} = {escaped};'
    if field == "display_name":
        return re.sub(
            r'(card_name\s*=\s*"(?:\\.|[^"\\])*";)',
            lambda m: m.group(1) + insert,
            body,
            count=1,
        )
    return body


def _patch_lua_file(text: str, cards: dict[str, dict[str, str]], messages: dict[str, str]) -> str:
    # Brace-based rewrite of each card table
    out = []
    last = 0
    for m in re.finditer(r'g_ascension_cards\["([^"]+)"\]\s*=\s*\{', text):
        out.append(text[last : m.end() - 1])
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    body = text[start + 1 : i]
                    row = cards.get(m.group(1))
                    if row:
                        # card_name is the Lua id — never translate it.
                        # display_name is what the gallery title reads when loc is skipped.
                        if row.get("display_name"):
                            body = _replace_field(body, "display_name", row["display_name"])
                        if row.get("effect_text"):
                            body = _replace_field(body, "effect_text", row["effect_text"])
                        if row.get("flavor_text"):
                            body = _replace_field(body, "flavor_text", row["flavor_text"])
                    out.append("{")
                    out.append(body)
                    out.append("}")
                    last = i + 1
                    break
            elif ch == '"':
                i += 1
                while i < len(text):
                    if text[i] == "\\":
                        i += 2
                        continue
                    if text[i] == '"':
                        break
                    i += 1
            i += 1
        else:
            out.append(text[start:])
            last = len(text)
            break
    out.append(text[last:])
    patched = "".join(out)

    for en, zh in messages.items():
        patched = patched.replace(en, zh)
    return patched


def enable(locale: str) -> None:
    game = detect_game_root(prompt=True)
    src = lua_dir(game)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_lua = BACKUP_DIR / "Lua"
    if not backup_lua.exists():
        shutil.copytree(src, backup_lua)
        print(f"backed up Lua -> {backup_lua}")
    else:
        for path in backup_lua.glob("*.lua"):
            shutil.copy2(path, src / path.name)
        print(f"restored clean Lua from {backup_lua} before applying")

    cards = _load_card_map(locale)
    messages = _load_messages(locale)
    changed = 0
    for path in sorted(src.glob("*.lua")):
        original = path.read_text(encoding="utf-8", errors="replace")
        patched = _patch_lua_file(original, cards, messages)
        if patched != original:
            path.write_text(patched, encoding="utf-8", newline="\n")
            changed += 1
    cfg = load_patch_config()
    cfg["enabled"] = True
    cfg["locale"] = locale
    save_patch_config(cfg)
    (BACKUP_DIR / "applied.json").write_text(
        json.dumps({"locale": locale, "luaFilesChanged": changed}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"enabled {locale}: rewrote {changed} Lua files in {src}")

    loc = LOCALE_DIR[locale]
    replacements = {}
    cards_csv = loc / "cards.csv"
    packed_csv = loc / "cards_packed.csv"
    tutorial_asset = loc / "tutorial_asset.csv"
    if packed_csv.is_file():
        replacements["cards_EN"] = packed_csv
    elif cards_csv.is_file():
        replacements["cards_EN"] = cards_csv
    # Keep tutorial_EN English. Packed UTF-8 Chinese becomes mojibake in that TextAsset.
    if replacements:
        try:
            apply_textassets(game, replacements)
        except Exception as exc:
            print(f"asset overlay skipped: {exc}")

    loc_map: dict[str, str] = {}
    cards_csv = loc / "cards.csv"
    if cards_csv.is_file():
        with cards_csv.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0]:
                    loc_map[row[0]] = row[1]
    for ui_path in (loc / "ui.csv", loc / "ui.full.csv"):
        if not ui_path.is_file():
            continue
        with ui_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                key = row.get("key") or ""
                zh = row.get("zh") or ""
                if key.startswith("Key_") and zh:
                    loc_map[key] = zh
    if loc_map:
        try:
            apply_loc_json(game, loc_map)
        except Exception as exc:
            print(f"loc JSON overlay skipped: {exc}")

    try:
        apply_scene_strings(game)
    except Exception as exc:
        print(f"scene overlay skipped: {exc}")

    # Do not UnityPy-rewrite resources.assets for rulebook: a full reserialize
    # hung in-game loading. Rulebook TMP stays a runtime overlay.

    try:
        from overlay import write_overlay  # noqa: E402

        overlay_src = write_overlay()
        overlay_dest = streaming_zh_overlay(game)
        overlay_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay_src, overlay_dest)
        print(f"overlay -> {overlay_dest}")
    except Exception as exc:
        print(f"overlay skipped: {exc}")

    try:
        font_path = streaming_zh_font(game)
        font_path.parent.mkdir(parents=True, exist_ok=True)
        font_path.write_bytes(subset_font(collect_charset()))
        print(f"CJK subset -> {font_path}")
    except Exception as exc:
        print(f"CJK subset skipped: {exc}")

    try:
        enable_runtime(game)
    except Exception as exc:
        print(f"runtime font plugin skipped: {exc}")

    print("Close the game before enabling. Steam 'Verify integrity' will undo overlays.")


def disable() -> None:
    game = detect_game_root(prompt=True)
    src = lua_dir(game)
    backup_lua = BACKUP_DIR / "Lua"
    if not backup_lua.is_dir():
        raise FileNotFoundError(f"No Lua backup at {backup_lua}. Nothing to restore.")
    for path in backup_lua.glob("*.lua"):
        shutil.copy2(path, src / path.name)
    restore_assets(game)
    restore_level1(game)
    zh_dir = streaming_zh_dir(game)
    for extra in (streaming_zh_font(game), streaming_zh_overlay(game), zh_dir / "plugin.log"):
        if extra.is_file():
            extra.unlink()
    if zh_dir.is_dir() and not any(zh_dir.iterdir()):
        zh_dir.rmdir()
    try:
        disable_runtime(game)
    except Exception as exc:
        print(f"BepInEx uninstall skipped: {exc}")
    cfg = load_patch_config()
    cfg["enabled"] = False
    save_patch_config(cfg)
    print(f"disabled: restored Lua from {backup_lua}")


def status() -> None:
    cfg = load_patch_config()
    game = detect_game_root(cfg, prompt=True)
    backup = BACKUP_DIR / "Lua"
    print(f"enabled: {cfg.get('enabled')}")
    print(f"locale:  {cfg.get('locale')}")
    print(f"game:    {game}")
    print(f"backup:  {backup} ({'yes' if backup.is_dir() else 'no'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Toggle the Ascension Chinese overlay.")
    parser.add_argument("command", choices=["enable", "disable", "status"])
    parser.add_argument(
        "--locale",
        default=None,
        choices=["zh-Hans", "zh-Hant"],
        help="Override patch.json locale when enabling",
    )
    args = parser.parse_args()
    if args.command == "status":
        status()
        return
    if args.command == "disable":
        disable()
        return
    cfg = load_patch_config()
    locale = args.locale or cfg.get("locale") or "zh-Hans"
    enable(locale)


if __name__ == "__main__":
    main()
