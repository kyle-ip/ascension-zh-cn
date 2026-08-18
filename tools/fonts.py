"""Subset a CJK TTF for the BepInEx plugin (StreamingAssets/zh-cn).

Do not splice this into resources.assets or flip TMP atlas modes — that
corrupted the file (Unity: Position out of bounds) and crashed on launch.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root, resources_assets  # noqa: E402

FONT_OUT = ROOT / "fonts" / "NotoSansSC-overlay.ttf"
WINDOWS_SOURCES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def collect_charset() -> str:
    chars = set(chr(i) for i in range(32, 127))
    chars.update("、。；：？！「」『』（）《》【】—…·•°×÷￥")
    chars.update("内购店应用商店离线在线菜单退出订阅通讯请出牌结束回合")
    overlay = ROOT / "loc" / "zh-Hans" / "overlay.tsv"
    if overlay.is_file():
        chars.update(overlay.read_text(encoding="utf-8"))
    for folder in (ROOT / "loc" / "zh-Hans", ROOT / "glossary"):
        if not folder.is_dir():
            continue
        for path in folder.glob("*.csv"):
            chars.update(path.read_text(encoding="utf-8"))
    keep = []
    for ch in sorted(chars):
        o = ord(ch)
        if o < 32:
            continue
        if (
            o < 127
            or 0x00A0 <= o <= 0x00FF
            or 0x2000 <= o <= 0x206F
            or 0x3000 <= o <= 0x303F
            or 0x3400 <= o <= 0x4DBF
            or 0x4E00 <= o <= 0x9FFF
            or 0xF900 <= o <= 0xFAFF
            or 0xFF00 <= o <= 0xFFEF
        ):
            keep.append(ch)
    return "".join(keep)


def _find_source_font() -> Path:
    bundled = [
        p
        for p in list((ROOT / "fonts").glob("*.ttf")) + list((ROOT / "fonts").glob("*.otf"))
        if p.name != FONT_OUT.name and p.suffix.lower() in {".ttf", ".otf", ".ttc"}
    ]
    if bundled:
        return bundled[0]
    for path in WINDOWS_SOURCES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "No CJK source font. Put an OFL TTF/OTF in fonts/ or install Microsoft YaHei."
    )


def subset_font(charset: str) -> bytes:
    from fontTools.subset import Options, Subsetter
    from fontTools.ttLib import TTFont

    src = _find_source_font()
    FONT_OUT.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if src.suffix.lower() == ".ttc":
        kwargs["fontNumber"] = 0
    font = TTFont(str(src), **kwargs)
    options = Options()
    options.desubroutinize = True
    options.hinting = False
    options.layout_features = []
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.drop_tables += [
        "DSIG",
        "FFTM",
        "GSUB",
        "GPOS",
        "GDEF",
        "BASE",
        "JSTF",
        "kern",
        "vhea",
        "vmtx",
        "VORG",
        "meta",
        "MVAR",
        "STAT",
    ]
    subsetter = Subsetter(options=options)
    subsetter.populate(text=charset)
    subsetter.subset(font)
    tmp = FONT_OUT.with_suffix(".tmp.ttf")
    font.save(tmp)
    data = tmp.read_bytes()
    tmp.unlink(missing_ok=True)
    FONT_OUT.write_bytes(data)
    print(f"subset {src.name} -> {FONT_OUT.name} ({len(data)} bytes, {len(charset)} chars)")
    return data


def _replace_font_blob(assets: bytes, new_ttf: bytes) -> bytes:
    import UnityPy

    env = UnityPy.load(str(resources_assets(detect_game_root())))
    font_obj = None
    fallback_obj = None
    for obj in env.objects:
        if obj.type.name == "Font" and obj.path_id == 1882:
            font_obj = obj
        if obj.type.name == "MonoBehaviour" and obj.path_id == 27218:
            fallback_obj = obj
    if font_obj is None:
        raise FileNotFoundError("LiberationSans Font object not found")

    tree = font_obj.read_typetree(check_read=False)
    original = bytes(tree["m_FontData"])
    if len(new_ttf) > len(original):
        raise ValueError(
            f"CJK subset is {len(new_ttf)} bytes, original TTF is {len(original)}; "
            "cannot grow the packed Font"
        )
    needle = original[:80]
    start = assets.find(needle)
    if start < 0:
        raise RuntimeError("LiberationSans TTF blob not found in resources.assets")
    padded = new_ttf + (b"\x00" * (len(original) - len(new_ttf)))
    out = bytearray(assets)
    out[start : start + len(original)] = padded

    if fallback_obj is not None:
        raw = fallback_obj.get_raw_data()
        pptr = struct.pack("<q", 1882)
        rel = raw.find(pptr)
        if rel >= 0:
            mode_off = rel + 8
            mode = struct.unpack_from("<i", raw, mode_off)[0]
            abs_off = fallback_obj.byte_start + mode_off
            if mode == 0:
                struct.pack_into("<i", out, abs_off, 1)
                print("set LiberationSans SDF - Fallback atlas mode to Dynamic")
            else:
                print(f"fallback atlasPopulationMode already {mode}")
    print(f"replaced LiberationSans TTF ({len(original)} bytes, subset {len(new_ttf)})")
    return bytes(out)


def apply_cjk_font(game_root: Path, ttf: bytes | None = None) -> None:
    path = resources_assets(game_root)
    data = path.read_bytes()
    if ttf is None:
        ttf = subset_font(collect_charset())
    path.write_bytes(_replace_font_blob(data, ttf))
    print(f"wrote CJK font into {path}")


def main() -> None:
    charset = collect_charset()
    ttf = subset_font(charset)
    print("ttf", len(ttf), "chars", len(charset))


if __name__ == "__main__":
    main()
