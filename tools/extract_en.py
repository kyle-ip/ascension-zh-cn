"""Extract English localization blobs from the installed Unity assets."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root, lua_dir, resources_assets  # noqa: E402

OUT_EN = ROOT / "loc" / "en"


def _read_cstring(data: bytes, start: int, max_len: int = 4_000_000) -> str:
    end = data.find(b"\x00", start)
    if end < 0 or end - start > max_len:
        end = start + max_len
    return data[start:end].decode("utf-8", "replace")


def extract_named_csv(data: bytes, asset_name: bytes) -> str | None:
    idx = data.find(asset_name)
    if idx < 0:
        return None
    # Skip the name and a few type bytes, then find the first KEY-like line.
    window = data[idx : idx + 80]
    for marker in (b"LABEL_", b"TUTORIAL_", b"CARDNAME_"):
        rel = window.find(marker)
        if rel >= 0:
            return _read_cstring(data, idx + rel)
    # Fallback: first printable run after the name
    return _read_cstring(data, idx + len(asset_name) + 2)


def extract_ui_keys(data: bytes) -> list[tuple[str, str]]:
    """Pull Key_* + English column from every localization sheet JSON."""
    merged: dict[str, str] = {}
    for m in re.finditer(rb'"1:1":"Key","1:2":"EN"', data):
        region = data[m.start() : m.start() + 400_000].decode("utf-8", "replace")
        keys: dict[int, str] = {}
        ens: dict[int, str] = {}
        for row, key in re.findall(r'"(\d+):1":"(Key_[^"]+)"', region):
            keys[int(row)] = key
        for row, val in re.findall(r'"(\d+):2":"(.*?)"', region):
            r = int(row)
            if r == 1:
                continue
            try:
                ens[r] = val.encode("utf-8").decode("unicode_escape")
            except Exception:
                ens[r] = val
        for r, key in keys.items():
            if key not in merged:
                merged[key] = ens.get(r, "")
    return [(k, merged[k]) for k in sorted(merged)]


def _lua_string_field(body: str, name: str) -> str:
    fm = re.search(
        rf'{name}\s*=\s*((?:"(?:\\.|[^"\\])*"(?:\s*\.\.\s*)?)+)',
        body,
    )
    if not fm:
        return ""
    parts = re.findall(r'"((?:\\.|[^"\\])*)"', fm.group(1))
    return "".join(bytes(p, "utf-8").decode("unicode_escape") for p in parts)


def _extract_balanced_tables(text: str) -> list[tuple[str, str]]:
    cards = []
    for m in re.finditer(r'g_ascension_cards\["([^"]+)"\]\s*=\s*\{', text):
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            ch = text[i]
            if ch == "{" :
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cards.append((m.group(1), text[start + 1 : i]))
                    break
            elif ch == '"':
                i += 1
                while i < len(text):
                    if text[i] == "\\" :
                        i += 2
                        continue
                    if text[i] == '"':
                        break
                    i += 1
            i += 1
    return cards


def extract_lua_cards(game_root) -> list[dict]:
    from common import BACKUP_DIR

    backup = BACKUP_DIR / "Lua"
    lua = backup if backup.is_dir() else lua_dir(game_root)
    cards = []
    for path in sorted(lua.glob("*.lua")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for card_id, body in _extract_balanced_tables(text):
            card_name = _lua_string_field(body, "card_name") or card_id
            cards.append(
                {
                    "id": card_id,
                    "card_name": card_name,
                    "display_name": _lua_string_field(body, "display_name") or card_name,
                    "card_set": _lua_string_field(body, "card_set"),
                    "card_type": _lua_string_field(body, "card_type"),
                    "effect_text": _lua_string_field(body, "effect_text"),
                    "flavor_text": _lua_string_field(body, "flavor_text"),
                    "source_file": path.name,
                }
            )
    return cards


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    game = detect_game_root()
    assets = resources_assets(game).read_bytes()
    OUT_EN.mkdir(parents=True, exist_ok=True)

    for name, outfile in (
        (b"cards_EN", OUT_EN / "cards_en_raw.csv"),
        (b"tutorial_EN", OUT_EN / "tutorial.csv"),
        (b"tutorial_desktop_EN", OUT_EN / "tutorial_desktop.csv"),
        (b"tutorial_mobile_EN", OUT_EN / "tutorial_mobile.csv"),
    ):
        blob = extract_named_csv(assets, name)
        if blob:
            outfile.write_text(blob.replace("\r\n", "\n"), encoding="utf-8")
            print(f"wrote {outfile.name} ({blob.count(chr(10))+1} lines)")
        else:
            print(f"missing asset {name.decode()}")

    ui = extract_ui_keys(assets)
    write_csv(
        OUT_EN / "ui.csv",
        [{"key": k, "en": v} for k, v in ui],
        ["key", "en"],
    )
    print(f"wrote ui.csv ({len(ui)} keys)")

    cards = extract_lua_cards(game)
    write_csv(
        OUT_EN / "lua_cards.csv",
        cards,
        [
            "id",
            "card_name",
            "display_name",
            "card_set",
            "card_type",
            "effect_text",
            "flavor_text",
            "source_file",
        ],
    )
    print(f"wrote lua_cards.csv ({len(cards)} cards)")

    summary = {
        "gameRoot": str(game),
        "uiKeys": len(ui),
        "luaCards": len(cards),
    }
    (OUT_EN / "extract_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
