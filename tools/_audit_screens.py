"""Audit leftover screens from user screenshots. ASCII stdout."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Ascension")
ZH = ROOT / "loc" / "zh-Hans"
EN_SHEETS = ROOT / "loc" / "en" / "sheets"
LUA = GAME / "AscensionGame_Data" / "StreamingAssets" / "Lua"


def load_keys(path: Path) -> set[str]:
    out: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if row and row[0] and row[0] not in {"key", "en"}:
                out.add(row[0])
    return out


en_keys = load_keys(EN_SHEETS / "Ascension_Cards.csv")
zh_keys = load_keys(ZH / "cards.csv")
missing = sorted(en_keys - zh_keys)
pref = Counter(k.split("_")[0] for k in missing)
print("Ascension_Cards", len(en_keys), "cards.csv", len(zh_keys), "missing", len(missing))
print("missing prefix", dict(pref))
print("has EFFECT_ENLIGHTENEDREMNANT in zh", "EFFECT_ENLIGHTENEDREMNANT" in zh_keys)
print("has CARDNAME_ENLIGHTENEDREMNANT in zh", "CARDNAME_ENLIGHTENEDREMNANT" in zh_keys)

raw_keys = load_keys(ROOT / "loc" / "en" / "cards_en_raw.csv")
print("cards_en_raw", len(raw_keys), "sheet-not-in-raw", len(en_keys - raw_keys))

latin = re.compile(r"[A-Za-z]{4,}")
cjk = re.compile(r"[\u4e00-\u9fff]")
mixed = en_only = concat = 0
concat_samples = []
for p in sorted(LUA.glob("*_cards.lua")):
    text = p.read_text(encoding="utf-8", errors="replace")
    concat += len(re.findall(r'effect_text\s*=\s*"[^"]+"\s*\.\.', text))
    for m in re.finditer(r'g_ascension_cards\["([^"]+)"\]', text):
        pass
    for m in re.finditer(r'effect_text\s*=\s*((?:"(?:\\.|[^"\\])*"(?:\s*\.\.\s*)?)+)', text):
        blob = m.group(1)
        if latin.search(blob):
            if cjk.search(blob):
                mixed += 1
                if len(concat_samples) < 6:
                    concat_samples.append(blob.replace("\n", " ")[:120])
            else:
                en_only += 1
print("lua effect_text mixed", mixed, "english-only", en_only, "concat operators", concat)
for s in concat_samples:
    print(" SAMPLE", s)

needles = [
    b"Offline Games",
    b"OfflineGames",
    b"Downloadable Content",
    b"DownloadableContent",
    b"DECKBUILDING GAME",
    b"Deckbuilding Game",
    b"Sign up to get the latest",
    b"STONE BLADE NEWSLETTER",
    b"For millennia",
    b"PLAY ORDER",
    b"Muses of Malevolence",
    b"Owned",
    b"Promo 7",
    b"Rulebook",
]
data_dir = GAME / "AscensionGame_Data"
candidates = [
    data_dir / "level1",
    data_dir / "level2",
    data_dir / "resources.assets",
    data_dir / "sharedassets0.assets",
    data_dir / "sharedassets1.assets",
    data_dir / "sharedassets2.assets",
]
print("--- binary needles ---")
for path in candidates:
    if not path.is_file():
        print("missing", path.name)
        continue
    data = path.read_bytes()
    hits = []
    for n in needles:
        c = data.count(n)
        if c:
            hits.append(f"{n.decode('ascii', 'replace')} x{c}")
    print(path.name, "; ".join(hits) if hits else "(none of listed)")

ui_en = load_keys(EN_SHEETS / "Common_Strings.csv")
ui_zh = load_keys(ZH / "ui.csv")
print("Common_Strings", len(ui_en), "ui.csv", len(ui_zh), "missing ui", len(ui_en - ui_zh))
for k in sorted(ui_en - ui_zh)[:30]:
    print(" UI missing", k)

print("--- IAP / titles ---")
res = (GAME / "AscensionGame_Data" / "resources.assets").read_bytes()
level1 = (GAME / "AscensionGame_Data" / "level1").read_bytes()
iap = sorted({m.group(1).decode() for m in re.finditer(rb'"((?:IAP_|DLC_)[A-Za-z0-9_]+)"', res)})
print("IAP/DLC keys in resources", len(iap))
for k in iap:
    print(" ", k)
for blob, label in ((res, "resources"), (level1, "level1")):
    for n in (
        b"DownloadableContent",
        b"Downloadable Content",
        b"PLAY ORDER",
        b"RESOURCES:",
        b"Godslayer",
        b"Newsletter",
        b"ButtonCancel",
        b"IAP_Owned",
    ):
        print(label, n.decode(), blob.count(n))
