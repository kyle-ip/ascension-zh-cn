"""Regression: long-text normalize must replace tags with spaces."""
from pathlib import Path

PUNC = {
    0x2014: "-",
    0x2013: "-",
    0x2018: "'",
    0x2019: "'",
    0x201C: '"',
    0x201D: '"',
    0x2026: ".",
    0xA0: " ",
    0x3000: " ",
}


def normalize(text: str) -> str:
    sb = []
    in_tag = False
    prev = False
    for c in text:
        if c == "<":
            in_tag = True
            if not prev:
                sb.append(" ")
                prev = True
            continue
        if in_tag:
            if c == ">":
                in_tag = False
            continue
        if c == "\\":
            continue
        mapped = PUNC.get(ord(c), c)
        if mapped.isspace() or mapped in "\r\n":
            if not prev:
                sb.append(" ")
                prev = True
            continue
        prev = False
        if "A" <= mapped <= "Z":
            mapped = chr(ord(mapped) + 32)
        sb.append(mapped)
    return "".join(sb).strip()


def test_br_tag_becomes_space():
    assert normalize("unique<br>new") == "unique new"
    assert normalize("unique<br/>new") == "unique new"


def test_store_blurb_matches_overlay():
    root = Path(__file__).resolve().parents[1]
    ov = root / "loc" / "zh-Hans" / "overlay.tsv"
    exact = {}
    for ln in ov.read_text(encoding="utf-8").splitlines():
        if not ln or ln[0] == "#":
            continue
        parts = ln.split("\t")
        if len(parts) < 3 or parts[0] != "E":
            continue
        exact[parts[1]] = parts[2]
    key = next(k for k in exact if "Muses of Malevolence" in k)
    # Simulate game text: ASCII apostrophe, no rich tags, newlines for <br>
    import re

    game = re.sub(r"<br\s*/?>", "\n", key, flags=re.I)
    game = re.sub(r"<[^>]+>", "", game)
    game = game.replace("\u2019", "'").replace("\u2018", "'")
    assert normalize(game) == normalize(key)
    # Dictionary hit
    norm = {normalize(k): v for k, v in exact.items() if len(normalize(k)) >= 4}
    assert normalize(game) in norm


def test_rulebook_millennia_in_overlay():
    root = Path(__file__).resolve().parents[1]
    ov = root / "loc" / "zh-Hans" / "overlay.tsv"
    text = ov.read_text(encoding="utf-8")
    assert "For millennia" in text
    assert "千百年来" in text
