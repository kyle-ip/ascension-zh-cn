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
)

LOCALE_DIR = {
    "zh-Hans": ROOT / "loc" / "zh-Hans",
    "zh-Hant": ROOT / "loc" / "zh-Hant",
}


def _lua_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
    pattern = re.compile(rf'({field}\s*=\s*)"(?:\\.|[^"\\])*"')
    repl = rf'\1"{_lua_escape(new_value)}"'
    if pattern.search(body):
        return pattern.sub(repl, body, count=1)
    # Concatenated strings: replace the whole assignment RHS through the semicolon/newline
    pattern2 = re.compile(
        rf'({field}\s*=\s*)(?:"(?:\\.|[^"\\])*"(?:\s*\.\.\s*)?)+'
    )
    if pattern2.search(body):
        return pattern2.sub(repl, body, count=1)
    insert = f'\n   {field} = "{_lua_escape(new_value)}";'
    # Insert after card_name if we are adding display_name
    if field == "display_name":
        return re.sub(
            r'(card_name\s*=\s*"(?:\\.|[^"\\])*";)',
            rf"\1{insert}",
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
                    card = cards.get(m.group(1))
                    if card:
                        if card.get("display_name"):
                            body = _replace_field(body, "display_name", card["display_name"])
                        if card.get("effect_text"):
                            body = _replace_field(body, "effect_text", card["effect_text"])
                        if card.get("flavor_text"):
                            body = _replace_field(body, "flavor_text", card["flavor_text"])
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
    game = detect_game_root()
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
    print("Close the game before enabling. Steam 'Verify integrity' will undo overlays.")


def disable() -> None:
    game = detect_game_root()
    src = lua_dir(game)
    backup_lua = BACKUP_DIR / "Lua"
    if not backup_lua.is_dir():
        raise FileNotFoundError(f"No Lua backup at {backup_lua}. Nothing to restore.")
    for path in backup_lua.glob("*.lua"):
        shutil.copy2(path, src / path.name)
    cfg = load_patch_config()
    cfg["enabled"] = False
    save_patch_config(cfg)
    print(f"disabled: restored Lua from {backup_lua}")


def status() -> None:
    cfg = load_patch_config()
    game = detect_game_root(cfg)
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
