"""Rebuild glossary/terms.csv from glossary/zh-Hans.csv (Hans is canonical)."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "glossary" / "zh-Hans.csv"
DST = ROOT / "glossary" / "terms.csv"


def main() -> None:
    rows: list[dict[str, str]] = []
    with SRC.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            en = (row.get("en") or "").strip()
            zh = (row.get("zh") or "").strip()
            if not en or en.startswith("#") or not zh:
                continue
            rows.append(
                {
                    "english": en,
                    "zh_hans": zh,
                    "zh_hant": zh,
                    "source": (row.get("source") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                }
            )
    with DST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["english", "zh_hans", "zh_hant", "source", "notes"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {DST.relative_to(ROOT)} ({len(rows)} terms from {SRC.name})")


if __name__ == "__main__":
    main()
