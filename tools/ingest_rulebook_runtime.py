"""Append rulebook-like strings from untranslated.tsv into loc/en/rulebook.csv."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root  # noqa: E402

EN = ROOT / "loc" / "en" / "rulebook.csv"
DUMP = Path(detect_game_root()) / "AscensionGame_Data" / "StreamingAssets" / "zh-cn" / "untranslated.tsv"


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


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fingerprint(s: str) -> str:
    s = normalize(s).replace("\t", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return re.sub(r"[^A-Za-z0-9]+", "", s)[:120]


SKIP_MARKERS = (
    "Promo Cards Included",
    "bundle of promo",
    "Ascension bundles",
    "Playdek account",
    "Confirmation Popup",
    "support@playdek",
    "Change resolution",
    "Share your gameplay",
    "Senior Product Manager",
    "Chief Executive",
    "stand alone sets",
    "favorite fan bundle",
    "Unique new cards per set",
    "Game Design",
    "Harness elemental magic",
    "Deck Building Game",
)


def looks_rulebook(text: str) -> bool:
    if len(text) < 100:
        return False
    low = text.lower()
    if any(m.lower() in low for m in SKIP_MARKERS):
        return False
    letters = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    if letters < 40:
        return False
    markers = (
        "margin-right",
        "margin-left",
        "center row",
        "honor",
        "energize",
        "soul gem",
        "trophy",
        "event",
        "transform",
        "fate",
        "vigil",
        "deofol",
        "divinations",
        "portal deck",
        "always available",
        "keystone",
        "temple",
        "rally",
        "recur",
        "insight",
        "dream",
        "rune",
        "construct",
        "monster",
        "hero",
        "banish",
        "acquire",
        "defeat",
        "samael",
        "kythis",
        "adayu",
        "erabus",
        "aklys",
    )
    return any(m in low for m in markers)


def main() -> None:
    rows = list(csv.DictReader(EN.open(encoding="utf-8-sig", newline="")))
    seen = {fingerprint(r["en"]) for r in rows}
    added = 0
    if DUMP.is_file():
        for line in DUMP.read_text(encoding="utf-8").splitlines():
            if not line.startswith("E\t"):
                continue
            text = unescape_dump(line.split("\t")[1])
            if not looks_rulebook(text):
                continue
            fp = fingerprint(text)
            if fp in seen:
                continue
            seen.add(fp)
            rows.append(
                {
                    "set": "runtime",
                    "go_name": "untranslated",
                    "en": text,
                    "norm": normalize(text),
                    "from_card": "",
                }
            )
            added += 1

    with EN.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "go_name", "en", "norm", "from_card"])
        w.writeheader()
        w.writerows(rows)
    print(f"rulebook.csv now {len(rows)} rows (+{added} from untranslated)")


if __name__ == "__main__":
    main()
