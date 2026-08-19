"""Find rulebook bodies present at runtime but missing from loc/en/rulebook.csv."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root, resources_assets  # noqa: E402

EN = ROOT / "loc" / "en" / "rulebook.csv"
DUMP = Path(detect_game_root()) / "AscensionGame_Data" / "StreamingAssets" / "zh-cn" / "untranslated.tsv"
OUT = ROOT / "loc" / "en" / "rulebook_runtime_gaps.csv"


def unescape_dump(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            c = raw[i + 1]
            if c == "n":
                out.append("\n")
                i += 2
                continue
            if c == "r":
                out.append("\r")
                i += 2
                continue
            if c == "t":
                out.append("\t")
                i += 2
                continue
            if c == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(raw[i])
        i += 1
    return "".join(out)


def collapse(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    s = re.sub(r" *\n *", "\n", s)
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s.strip()


def fingerprint(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", collapse(s))[:96]


def looks_rulebook(text: str) -> bool:
    if len(text) < 80:
        return False
    if not re.search(r"[A-Za-z]{12,}", text):
        return False
    markers = (
        "margin-right",
        "center row",
        "Honor",
        "Energize",
        "Soul Gem",
        "Trophy",
        "Event",
        "Transform",
        "Fate",
        "Vigil",
        "Deofol",
        "Players =",
        "divinations",
        "Portal Deck",
        "Always Available",
        "Keystone",
        "Temple",
        "Rally",
        "Recur",
        "Dream",
        "Insight",
        "What's New",
    )
    low = text.lower()
    if any(m.lower() in low for m in markers):
        return True
    if text.count("\n") >= 2 and len(text) > 400:
        return True
    return False


def load_existing() -> set[str]:
    fps: set[str] = set()
    with EN.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            for key in ("en", "norm"):
                v = row.get(key) or ""
                if v:
                    fps.add(fingerprint(v))
    return fps


def main() -> None:
    existing = load_existing()
    gaps: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in DUMP.read_text(encoding="utf-8").splitlines():
        if not line.startswith("E\t"):
            continue
        parts = line.split("\t")
        text = unescape_dump(parts[1])
        if not looks_rulebook(text):
            continue
        fp = fingerprint(text)
        if fp in existing or fp in seen:
            continue
        seen.add(fp)
        gaps.append(
            {
                "set": "runtime",
                "go_name": "untranslated",
                "en": text,
                "norm": collapse(text),
                "from_card": "",
            }
        )

    # Also scan assets for margin-right bodies that unity_strings may miss
    try:
        import UnityPy

        env = UnityPy.load(str(resources_assets(detect_game_root())))
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            raw = obj.get_raw_data()
            if b"margin-right" not in raw and b"divinations" not in raw:
                continue
            # Naive ASCII/UTF-8 scrape of long runs containing keywords
            for m in re.finditer(rb"(?:<margin-right=[^>]*>|My divinations)[\x09\x0a\x0d\x20-\x7e\xc0-\xff]{60,6000}", raw):
                try:
                    text = m.group(0).decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if not looks_rulebook(text):
                    continue
                fp = fingerprint(text)
                if fp in existing or fp in seen:
                    continue
                seen.add(fp)
                gaps.append(
                    {
                        "set": "asset",
                        "go_name": f"mb_{obj.path_id}",
                        "en": text,
                        "norm": collapse(text),
                        "from_card": "",
                    }
                )
    except Exception as ex:
        print("asset scan skipped:", ex)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "go_name", "en", "norm", "from_card"])
        w.writeheader()
        w.writerows(gaps)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(gaps)} gaps)")
    for g in gaps[:40]:
        print(f"  {len(g['en']):4d}  {g['norm'][:90].replace(chr(10), ' | ')}")


if __name__ == "__main__":
    main()
