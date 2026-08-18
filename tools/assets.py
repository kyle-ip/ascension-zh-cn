"""Same-size TextAsset replacement inside Unity resources.assets."""

from __future__ import annotations

import shutil
from pathlib import Path

from common import BACKUP_DIR, detect_game_root, resources_assets


def _replace_named_blob(data: bytes, asset_name: bytes, markers: tuple[bytes, ...], new_text: str) -> bytes:
    name_at = data.find(asset_name)
    if name_at < 0:
        raise FileNotFoundError(f"asset name not found: {asset_name.decode()}")
    start = -1
    window = data[name_at : name_at + 64]
    for marker in markers:
        rel = window.find(marker)
        if rel >= 0:
            start = name_at + rel
            break
    if start < 0:
        # search a bit further
        wider = data[name_at : name_at + 256]
        for marker in markers:
            rel = wider.find(marker)
            if rel >= 0:
                start = name_at + rel
                break
    if start < 0:
        raise FileNotFoundError(f"payload marker not found after {asset_name.decode()}")
    end = data.find(b"\x00", start)
    if end < 0:
        raise RuntimeError(f"unterminated payload for {asset_name.decode()}")
    original = data[start:end]
    payload = new_text.replace("\n", "\r\n") if "\r\n" not in new_text else new_text
    raw = payload.encode("utf-8")
    if raw.endswith(b"\x00"):
        raw = raw[:-1]
    if len(raw) > len(original):
        raise ValueError(
            f"{asset_name.decode()} Chinese blob is {len(raw)} bytes, "
            f"original is {len(original)}; cannot grow a packed TextAsset"
        )
    padded = raw + (b" " * (len(original) - len(raw)))
    return data[:start] + padded + data[end:]


def backup_assets(game_root: Path) -> Path:
    src = resources_assets(game_root)
    dest = BACKUP_DIR / "resources.assets"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"backed up {src.name} -> {dest}")
    return dest


def restore_named_blob(game_root: Path, asset_name: str, markers: tuple[bytes, ...]) -> None:
    """Copy one TextAsset payload back from the English backup."""
    backup = BACKUP_DIR / "resources.assets"
    if not backup.is_file():
        raise FileNotFoundError("no resources.assets backup")
    src = backup.read_bytes()
    dest_path = resources_assets(game_root)
    dest = bytearray(dest_path.read_bytes())
    name = asset_name.encode("ascii")

    def payload_span(data: bytes) -> tuple[int, int]:
        name_at = data.find(name)
        if name_at < 0:
            raise FileNotFoundError(f"asset name not found: {asset_name}")
        start = -1
        wider = data[name_at : name_at + 256]
        for marker in markers:
            rel = wider.find(marker)
            if rel >= 0:
                start = name_at + rel
                break
        if start < 0:
            raise FileNotFoundError(f"payload marker not found after {asset_name}")
        end = data.find(b"\x00", start)
        if end < 0:
            raise RuntimeError(f"unterminated payload for {asset_name}")
        return start, end

    s0, s1 = payload_span(src)
    d0, d1 = payload_span(bytes(dest))
    payload = src[s0:s1]
    if len(payload) != (d1 - d0):
        raise RuntimeError(
            f"{asset_name} size mismatch backup {len(payload)} vs live {d1 - d0}"
        )
    dest[d0:d1] = payload
    dest_path.write_bytes(dest)
    print(f"restored TextAsset {asset_name} from backup")


def restore_assets(game_root: Path) -> None:
    src = BACKUP_DIR / "resources.assets"
    if not src.is_file():
        print("no resources.assets backup; skip asset restore")
        return
    shutil.copy2(src, resources_assets(game_root))
    print(f"restored {src} -> resources.assets")


def apply_textassets(game_root: Path, replacements: dict[str, Path]) -> None:
    backup_assets(game_root)
    path = resources_assets(game_root)
    # Always start from the English backup so enable is idempotent.
    shutil.copy2(BACKUP_DIR / "resources.assets", path)
    blob = path.read_bytes()
    for name, csv_path in replacements.items():
        text = csv_path.read_text(encoding="utf-8")
        if name == "cards_EN":
            markers = (b"LABEL_REWARD",)
        elif name.startswith("tutorial"):
            markers = (b"TUTORIAL_TEXT_1", b"TUTORIAL_")
        else:
            markers = (text.encode("utf-8")[:12],)
        blob = _replace_named_blob(blob, name.encode("ascii"), markers, text)
        print(f"patched TextAsset {name} ({csv_path.name})")
    path.write_bytes(blob)
    print(f"wrote {path}")


def _json_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def apply_loc_json(game_root: Path, mapping: dict[str, str]) -> None:
    """Same-size EN-column replace inside packed Google Sheet JSON blobs only.

    Card faces and menus load these sheets (Ascension_Cards, Common_Strings),
    not Lua and not the cards_EN TextAsset. Do not run the regex over the
    whole assets file — that can rewrite binary and crash Unity.
    """
    import re

    path = resources_assets(game_root)
    data = bytearray(path.read_bytes())
    marker = b'"1:1":"Key"'
    pattern = re.compile(
        r'"(\d+):1":"((?:CARDNAME_|EFFECT_|LABEL_|FATE_|TROPHY_|ENERGY_|DAY_|NIGHT_|Key_|TUTORIAL_|FLAVOR_|IAP_|DLC_)[^"]+)","\1:2":"((?:\\.|[^"\\])*)"'.encode(
            "ascii"
        )
    )
    patched = 0
    skipped = 0
    blobs = 0
    pos = 0
    while True:
        start = data.find(marker, pos)
        if start < 0:
            break
        # Walk back to the JSON object start if present.
        json_at = data.rfind(b"{", max(0, start - 80), start)
        if json_at < 0:
            json_at = start
        end = data.find(b"\x00", start)
        if end < 0:
            break
        blob = bytes(data[json_at:end])
        blobs += 1

        def repl(match: re.Match[bytes]) -> bytes:
            nonlocal patched, skipped
            row = match.group(1)
            key = match.group(2).decode("ascii")
            old_val = match.group(3)
            if key.startswith("Key_Hint_") or key.startswith("TUTORIAL_"):
                return match.group(0)
            zh = mapping.get(key)
            if not zh:
                return match.group(0)
            new_val = _json_escape(zh).encode("utf-8")
            if len(new_val) > len(old_val):
                skipped += 1
                return match.group(0)
            padded = new_val + (b" " * (len(old_val) - len(new_val)))
            patched += 1
            return (
                b'"'
                + row
                + b':1":"'
                + match.group(2)
                + b'","'
                + row
                + b':2":"'
                + padded
                + b'"'
            )

        new_blob = pattern.sub(repl, blob)
        if len(new_blob) != len(blob):
            raise RuntimeError(
                f"loc JSON blob size changed {len(blob)} -> {len(new_blob)} at {json_at}"
            )
        data[json_at:end] = new_blob
        pos = end + 1

    path.write_bytes(data)
    print(f"patched loc JSON: {patched} cells in {blobs} sheets (skipped {skipped} too long)")
