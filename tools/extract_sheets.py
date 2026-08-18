"""Extract each packed loc JSON sheet into loc/en/sheets/."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from common import BACKUP_DIR, detect_game_root, resources_assets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "loc" / "en" / "sheets"

KEY_RE = re.compile(
    r'"(\d+):1":"((?:CARDNAME_|EFFECT_|LABEL_|FATE_|TROPHY_|ENERGY_|DAY_|NIGHT_|Key_|TUTORIAL_|FLAVOR_|IAP_|DLC_)[^"]+)"'
)
VAL_RE = re.compile(r'"(\d+):2":"((?:\\.|[^"\\])*)"')


def unescape(value: str) -> str:
    try:
        return json.loads('"' + value + '"')
    except Exception:
        return value.replace('\\"', '"').replace("\\n", "\n")


def extract_sheets() -> list[tuple[str, list[tuple[str, str]]]]:
    backup = BACKUP_DIR / "resources.assets"
    src = backup if backup.is_file() else resources_assets(detect_game_root())
    data = src.read_bytes()
    marker = b'"1:1":"Key"'
    pos = 0
    sheets: list[tuple[str, list[tuple[str, str]]]] = []
    while True:
        i = data.find(marker, pos)
        if i < 0:
            break
        json_at = data.rfind(b"{", max(0, i - 120), i)
        if json_at < 0:
            json_at = i
        end = data.find(b"\x00", i)
        blob = data[json_at:end].decode("utf-8", "replace")
        pre = data[max(0, json_at - 80) : json_at]
        names = re.findall(rb"[\x20-\x7e]{4,40}", pre)
        name = "unknown"
        for cand in (b"Common_Ingame", b"Ascension_Cards", b"Common_Strings", b"IconsAndLabels"):
            if cand in pre:
                name = cand.decode()
                break
        keys: dict[int, str] = {}
        vals: dict[int, str] = {}
        for row, key in KEY_RE.findall(blob):
            keys[int(row)] = key
        for row, val in VAL_RE.findall(blob):
            r = int(row)
            if r == 1:
                continue
            vals[r] = unescape(val)
        rows = [(keys[r], vals.get(r, "")) for r in sorted(keys)]
        sheets.append((name, rows))
        pos = end + 1
    return sheets


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sheets = extract_sheets()
    summary = []
    for name, rows in sheets:
        path = OUT / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["key", "en"])
            w.writerows(rows)
        leftover_key = sum(1 for k, _ in rows if k.startswith("Key_"))
        print(f"wrote {path.name} ({len(rows)} rows, Key_*={leftover_key})")
        summary.append({"name": name, "rows": len(rows)})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
