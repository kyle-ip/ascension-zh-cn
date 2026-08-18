"""Dry-run Lua overlay without writing the install."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch import _load_card_map, _patch_lua_file

cards = _load_card_map("zh-Hans")
src_path = (
    Path(__file__).resolve().parent.parent.parent
    / "AscensionGame_Data"
    / "StreamingAssets"
    / "Lua"
    / "set1_cards.lua"
)
src = src_path.read_text(encoding="utf-8")
out = _patch_lua_file(src, cards, {})
i = out.find('g_ascension_cards["Apprentice"]')
print(out[i : i + 500])
if "学徒" not in out:
    raise SystemExit("expected 学徒 in patched Lua")
print("ok")
