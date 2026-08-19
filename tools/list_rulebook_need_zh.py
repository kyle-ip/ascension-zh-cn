"""List EN rulebook strings that still need Chinese after glossary/exact."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

# Import after path setup
from build_rulebook_zh import fill_exact, load_glossary, load_card_names, translate_row, n  # noqa: E402

EN = ROOT / "loc" / "en" / "rulebook.csv"
OLD_ZH = ROOT / "loc" / "zh-Hans" / "rulebook.csv"
OUT = ROOT / "loc" / "en" / "rulebook_need_zh.json"


def main() -> None:
    fill_exact()
    glossary = load_glossary()
    names = load_card_names()
    old: dict[str, str] = {}
    if OLD_ZH.is_file():
        with OLD_ZH.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                en = n(row.get("en") or "")
                zh = row.get("zh") or ""
                if en and zh and re.search(r"[\u4e00-\u9fff]", zh):
                    old[en] = zh
                    EXACT_UPDATE = True
                    from build_rulebook_zh import EXACT

                    EXACT[en] = zh

    need = []
    seen = set()
    with EN.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            en = row["en"]
            key = n(en)
            if key in seen:
                continue
            seen.add(key)
            zh, source = translate_row(en, glossary, names)
            latin = len(re.findall(r"[A-Za-z]{5,}", re.sub(r"<[^>]+>", "", zh or "")))
            cjk = bool(re.search(r"[\u4e00-\u9fff]", zh or ""))
            if not zh or (latin >= 4 and not (cjk and latin < 8)):
                need.append({"set": row["set"], "go_name": row["go_name"], "en": en, "draft": zh or ""})
            elif latin >= 3:
                need.append({"set": row["set"], "go_name": row["go_name"], "en": en, "draft": zh or "", "soft": True})

    OUT.write_text(json.dumps(need, ensure_ascii=False, indent=2), encoding="utf-8")
    hard = [x for x in need if not x.get("soft")]
    print(f"need zh: {len(need)} (hard {len(hard)}) -> {OUT.relative_to(ROOT)}")
    for item in hard[:30]:
        print(f"  [{item['set']}] {item['en'][:90].replace(chr(10), ' | ')}")


if __name__ == "__main__":
    main()
