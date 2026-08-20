"""Clean L130+ machine-translation junk out of ui_runtime.csv.

ui_runtime.csv's first 129 rows are hand-vetted (key bindings / analytics
dialog / etc.).  Rows 130 onward are the result of running
``ingest_untranslated`` on a 2026-08-20 dump, and contain 298 rows of
card-effect word-replacement output applied to rulebook narrative and
DLC store paragraphs (e.g. ``Promo兽群 #6``, ``Network Connection迷失``,
``符文为一的两main resources在Ascension``).  Those paragraphs must live
in ``rulebook.csv`` (for human full-sentence translation) instead.

We keep rows 1..129 verbatim and drop everything after.  The next run of
``ingest_untranslated`` will re-ingest those paragraphs, but this time
``looks_rulebook_body`` routes them into ``rulebook.csv`` with empty zh
instead of poisoning ``ui_runtime.csv``.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "loc" / "zh-Hans" / "ui_runtime.csv"

LAST_KNOWN_GOOD_ROW = 129  # 1-indexed (includes header)

data = RUNTIME.read_bytes()
# Preserve BOM? original was UTF-8 no-BOM per git history.
if not RUNTIME.is_file():
    print("nothing to clean")
    sys.exit(0)

with RUNTIME.open("r", encoding="utf-8", newline="") as f:
    reader = csv.reader(f)
    rows = list(reader)

header = rows[0]
kept = rows[:LAST_KNOWN_GOOD_ROW]
dropped = rows[LAST_KNOWN_GOOD_ROW:]

print(f"Total rows (with header): {len(rows)}")
print(f"Keeping first {len(kept)} rows (rows 1..{LAST_KNOWN_GOOD_ROW})")
print(f"Dropping {len(dropped)} junk rows at L{LAST_KNOWN_GOOD_ROW+1}+")

# Sanity: header + LAST_KNOWN_GOOD_ROW-1 data rows = kept
assert kept[0] == ["en", "zh"], f"header mismatch: {kept[0]!r}"

with RUNTIME.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for r in kept:
        w.writerow(r)

print(f"rewrote {RUNTIME.name}")
