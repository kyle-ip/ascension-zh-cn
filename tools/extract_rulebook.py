"""Extract TMP strings from in-game Rulebook* prefabs into loc/en/rulebook.csv."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import UnityPy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root, resources_assets  # noqa: E402

OUT = ROOT / "loc" / "en" / "rulebook.csv"

PLACEHOLDER_RE = re.compile(r"This is the rules (?:part|area)", re.I)
TAG_RE = re.compile(r"</?(?:size|space|color|b|i|u|align|indent|margin-right|margin-left|sprite)[^>]*>", re.I)
SPRITE_ONLY_RE = re.compile(r"^(?:\s|<[^>]+>)*$", re.I)

SKIP_GO = {
    "RulebookCardTransform",
}


def unity_strings(raw: bytes) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = s.strip("\x00")
        if not s or s in seen:
            return
        if any(c.isalpha() for c in s) or "<sprite" in s.lower():
            seen.add(s)
            out.append(s)

    i = 0
    n = len(raw)
    while i + 4 <= n:
        ln = int.from_bytes(raw[i : i + 4], "little")
        if 2 <= ln <= 12000 and i + 4 + ln <= n:
            chunk = raw[i + 4 : i + 4 + ln]
            if all(
                b in (9, 10, 13) or 32 <= b < 127 or b >= 0x80
                for b in chunk
            ):
                try:
                    add(chunk.decode("utf-8"))
                    i += 4 + ln
                    continue
                except UnicodeDecodeError:
                    pass
        i += 1

    # Some TMP bodies are stored without a reliable length prefix for our scanner.
    # Allow full UTF-8 (curly quotes / em dashes appear in rulebook copy).
    for m in re.finditer(
        rb"(?:<margin-(?:right|left)=[^>]*>|<align=[^>]*>|My divinations|"
        rb"The game ends when|Soul Gems are|Event cards represent|"
        rb"Transform is a new|Dark Energy Shards|Energy <sprite|"
        rb"In Storm of Souls|When the worlds were born|"
        rb"It has been years since|The shadow of Deofol|"
        rb"Darkness has fallen over Vigil|"
        rb"An era of unprecedented)"
        rb"[\x09\x0a\x0d\x20-\x7e\x80-\xff]{40,12000}",
        raw,
    ):
        try:
            add(m.group(0).decode("utf-8"))
        except UnicodeDecodeError:
            pass
    return out


def deref(objs: dict, pptr):
    if pptr is None:
        return None
    pid = getattr(pptr, "m_PathID", None)
    if not pid:
        return None
    return objs.get(pid)


def go_name(go_obj) -> str:
    try:
        return go_obj.peek_name() or ""
    except Exception:
        return ""


def transform_of_go(objs: dict, go_obj):
    data = go_obj.read()
    for pair in data.m_Component:
        c = deref(objs, pair.component)
        if c and c.type.name in ("Transform", "RectTransform"):
            return c
    return None


def children_of_transform(objs: dict, tr_obj):
    try:
        tr = tr_obj.read()
    except Exception:
        return []
    out = []
    for k in tr.m_Children or []:
        kid = deref(objs, k)
        if kid:
            out.append(kid)
    return out


def mb_texts_on_go(objs: dict, go_obj) -> list[str]:
    data = go_obj.read()
    texts: list[str] = []
    for pair in data.m_Component:
        c = deref(objs, pair.component)
        if not c or c.type.name != "MonoBehaviour":
            continue
        for s in unity_strings(c.get_raw_data()):
            if s.startswith("Unity") or "TMPro" in s or s.startswith("m_"):
                continue
            texts.append(s)
    return texts


def pick_texts(go: str, candidates: list[str]) -> list[str]:
    interesting = "tmp" in go.lower() or "rules" in go.lower() or go in {"RulesFlavor", "RulesBase"}
    scored: list[str] = []
    for s in candidates:
        stripped = TAG_RE.sub("", s).replace("<br>", " ").strip()
        if PLACEHOLDER_RE.search(s):
            continue
        if SPRITE_ONLY_RE.match(stripped) and len(stripped) < 8:
            continue
        letters = sum(ch.isalpha() for ch in s)
        if letters < 3 and "<sprite" not in s.lower():
            continue
        if not interesting and letters < 20 and "<align" not in s.lower() and "<margin" not in s.lower():
            continue
        # Keep rulebook bodies even when a longer card-rules string shares the MB.
        if len(s) >= 80 or interesting or "<margin" in s.lower() or "<align" in s.lower():
            scored.append(s)
    # Prefer longer first but keep all unique.
    scored.sort(key=len, reverse=True)
    return scored


def walk_rulebook(objs: dict, root_go) -> list[tuple[str, str, str]]:
    tr = transform_of_go(objs, root_go)
    if not tr:
        return []
    rows: list[tuple[str, str, str]] = []
    q = [tr]
    seen: set[int] = set()
    while q:
        t = q.pop()
        if t.path_id in seen:
            continue
        seen.add(t.path_id)
        try:
            td = t.read()
            go = deref(objs, td.m_GameObject)
        except Exception:
            go = None
        if go:
            name = go_name(go)
            for text in pick_texts(name, mb_texts_on_go(objs, go)):
                rows.append((name, text, normalize(text)))
        q.extend(children_of_transform(objs, t))
    return rows


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def set_code(go_name_value: str) -> str:
    mapping = {
        "RulebookCotG": "cotg",
        "RulebookRotF": "rotf",
        "RulebookSoS": "sos",
        "RulebookIH": "ih",
        "RulebookRoV": "rov",
        "RulebookDU": "du",
        "RulebookRU": "ru",
        "RulebookDoC": "doc",
        "RulebookDS": "ds",
        "RulebookWoS": "wos",
        "RulebookGotE": "gote",
        "RulebookVotA": "vota",
        "RulebookDLRM": "dlrm",
        "RulebookDLV": "dlv",
        "RulebookASCL": "ascl",
        "Rulebook": "shell",
    }
    return mapping.get(go_name_value, go_name_value.lower())


def load_card_en(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for key in ("en", "effect", "name"):
                val = (row.get(key) or "").strip()
                if val:
                    out.add(normalize(val))
            if len(row) >= 2:
                out.add(normalize(list(row.values())[1]))
    return out


def extract() -> list[dict[str, str]]:
    env = UnityPy.load(str(resources_assets(detect_game_root())))
    objs = {o.path_id: o for o in env.objects}
    roots = []
    for obj in env.objects:
        if obj.type.name != "GameObject":
            continue
        name = go_name(obj)
        if name.startswith("Rulebook") and name not in SKIP_GO:
            roots.append((name, obj))

    card_en = load_card_en(ROOT / "loc" / "en" / "sheets" / "Ascension_Cards.csv")
    zh_cards = ROOT / "loc" / "zh-Hans" / "cards.csv"
    if zh_cards.is_file():
        with zh_cards.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2:
                    card_en.add(normalize(row[0]))

    rows: list[dict[str, str]] = []
    seen_pair: set[tuple[str, str]] = set()
    for root_name, go in sorted(roots):
        code = set_code(root_name)
        for go_n, en, norm in walk_rulebook(objs, go):
            key = (code, norm)
            if key in seen_pair:
                continue
            seen_pair.add(key)
            from_card = "1" if norm in card_en else ""
            rows.append(
                {
                    "set": code,
                    "go_name": go_n,
                    "en": en,
                    "norm": norm,
                    "from_card": from_card,
                }
            )
    return rows


def main() -> None:
    rows = extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "go_name", "en", "norm", "from_card"])
        w.writeheader()
        w.writerows(rows)
    unique = {r["norm"] for r in rows}
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows, {len(unique)} unique, {sum(len(r['en']) for r in rows)} chars)")
    by_set: dict[str, int] = {}
    for r in rows:
        by_set[r["set"]] = by_set.get(r["set"], 0) + 1
    for k, v in sorted(by_set.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main() or 0)
