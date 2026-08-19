"""Extract all localizable game text into loc/workbench/*.csv for human translation.

Preserves existing workbench `zh` / `status` when the same id or (area,en) reappears.
Also seeds from current loc/zh-Hans and glossary.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root  # noqa: E402

WB = ROOT / "loc" / "workbench"
EN = ROOT / "loc" / "en"
ZH = ROOT / "loc" / "zh-Hans"
GLOSSARY = ROOT / "glossary" / "zh-Hans.csv"

FIELDS_COMMON = [
    "id",
    "area",
    "match",
    "key",
    "context",
    "en",
    "zh",
    "status",
    "notes",
]


def norm(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def stable_id(area: str, *parts: str) -> str:
    raw = area + "\0" + "\0".join(parts)
    return area[:3] + "_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def status_for(zh: str, previous: str | None = None) -> str:
    if previous in {"done", "skip", "draft"} and zh:
        return previous
    if not (zh or "").strip():
        return "empty"
    if previous == "done":
        return "done"
    return "draft"


def load_wb_csv(name: str) -> dict[str, dict[str, str]]:
    path = WB / name
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rid = (row.get("id") or "").strip()
            if rid:
                out[rid] = row
    return out


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    WB.mkdir(parents=True, exist_ok=True)
    path = WB / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def merge_prev(row: dict[str, str], prev_by_id: dict[str, dict[str, str]], prev_by_en: dict[str, dict[str, str]]) -> dict[str, str]:
    old = prev_by_id.get(row["id"]) or prev_by_en.get(norm(row.get("en") or ""))
    if not old:
        row["status"] = status_for(row.get("zh") or "")
        return row
    zh = (old.get("zh") or "").strip() or (row.get("zh") or "").strip()
    notes = (old.get("notes") or "").strip() or (row.get("notes") or "")
    st = old.get("status") or ""
    row["zh"] = zh
    row["notes"] = notes
    row["status"] = status_for(zh, st)
    return row


def read_two_col(path: Path, k1: str, k2: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            a = (row.get(k1) or "").strip()
            b = row.get(k2) or ""
            if a:
                out[a] = b
    return out


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


def extract_rulebook(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    # Prefer fresh extract; fall back to existing en csv.
    try:
        from extract_rulebook import extract as extract_rb

        en_rows = extract_rb()
    except Exception as ex:
        print("rulebook live extract failed, using csv:", ex)
        en_path = EN / "rulebook.csv"
        en_rows = list(csv.DictReader(en_path.open(encoding="utf-8-sig", newline=""))) if en_path.is_file() else []

    zh_map: dict[str, str] = {}
    zh_path = ZH / "rulebook.csv"
    if zh_path.is_file():
        with zh_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                en = norm(row.get("en") or "")
                zh = row.get("zh") or ""
                if en and zh:
                    zh_map[en] = zh

    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in en_rows:
        en = item.get("en") or ""
        key = norm(en)
        if not key or key in seen or key in {"ultist", "ystic"}:
            continue
        seen.add(key)
        set_code = item.get("set") or ""
        go = item.get("go_name") or ""
        rid = stable_id("rulebook", set_code, key)
        row = {
            "id": rid,
            "area": "rulebook",
            "match": "exact",
            "key": "",
            "context": f"set={set_code};go={go}",
            "set": set_code,
            "go_name": go,
            "en": en,
            "zh": zh_map.get(key, ""),
            "status": "",
            "notes": "",
        }
        rows.append(merge_prev(row, prev, prev_en))
    return rows


def extract_ui_keys(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    en_map = read_two_col(EN / "ui.csv", "key", "en")
    if not en_map:
        en_map = read_two_col(EN / "sheets" / "Common_Strings.csv", "key", "en")
    # merge Common_Ingame
    for sheet in ("Common_Strings.csv", "Common_Ingame.csv"):
        p = EN / "sheets" / sheet
        if p.is_file():
            en_map.update(read_two_col(p, "key", "en"))
    zh_map = read_two_col(ZH / "ui.csv", "key", "zh")
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    for key in sorted(en_map):
        en = en_map[key]
        rid = stable_id("ui_keys", key)
        row = {
            "id": rid,
            "area": "ui_keys",
            "match": "key",
            "key": key,
            "context": key,
            "en": en,
            "zh": zh_map.get(key, ""),
            "status": "",
            "notes": "",
        }
        rows.append(merge_prev(row, prev, prev_en))
    return rows


def extract_ui_exact(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    """Hardcoded / runtime exact strings already curated."""
    sources = [
        ZH / "ui_runtime.csv",
        ZH / "combat_log.csv",
    ]
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    seen: set[str] = set()
    for path in sources:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                en = row.get("en") or ""
                zh = row.get("zh") or ""
                key = norm(en)
                if not key or key in seen:
                    continue
                seen.add(key)
                rid = stable_id("ui_exact", key)
                item = {
                    "id": rid,
                    "area": "ui_exact",
                    "match": "exact",
                    "key": "",
                    "context": path.name,
                    "en": en,
                    "zh": zh,
                    "status": "",
                    "notes": "",
                }
                rows.append(merge_prev(item, prev, prev_en))
    return rows


def extract_cards_lua(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    en_path = EN / "lua_cards.csv"
    zh_path = ZH / "lua_cards.csv"
    if not en_path.is_file():
        return []
    zh_by_id: dict[str, dict[str, str]] = {}
    if zh_path.is_file():
        with zh_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                zh_by_id[row.get("id") or ""] = row
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    with en_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            cid = row.get("id") or ""
            cset = row.get("card_set") or ""
            zh_row = zh_by_id.get(cid, {})
            for field in ("display_name", "effect_text", "flavor_text"):
                en = row.get(field) or ""
                if not en.strip():
                    continue
                rid = stable_id("cards_lua", cid, field)
                item = {
                    "id": rid,
                    "area": "cards_lua",
                    "match": "lua",
                    "key": "",
                    "context": f"card={cid};field={field};set={cset}",
                    "card_id": cid,
                    "card_set": cset,
                    "field": field,
                    "en": en,
                    "zh": zh_row.get(field) or "",
                    "status": "",
                    "notes": "",
                }
                rows.append(merge_prev(item, prev, prev_en))
    return rows


def extract_cards_sheet(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    en_path = EN / "sheets" / "Ascension_Cards.csv"
    zh_path = ZH / "cards.csv"
    if not en_path.is_file():
        return []
    en_map = read_two_col(en_path, "key", "en")
    zh_map: dict[str, str] = {}
    if zh_path.is_file():
        with zh_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2:
                    zh_map[row[0]] = row[1]
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    for key in sorted(en_map):
        en = en_map[key]
        rid = stable_id("cards_sheet", key)
        item = {
            "id": rid,
            "area": "cards_sheet",
            "match": "key",
            "key": key,
            "context": key,
            "en": en,
            "zh": zh_map.get(key, ""),
            "status": "",
            "notes": "",
        }
        rows.append(merge_prev(item, prev, prev_en))
    return rows


def extract_tutorial(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    en_map: dict[str, str] = {}
    for name in ("tutorial.csv", "tutorial_desktop.csv", "tutorial_mobile.csv"):
        p = EN / name
        if not p.is_file():
            continue
        with p.open(encoding="utf-8-sig", newline="") as f:
            sample = f.read(64)
        with p.open(encoding="utf-8-sig", newline="") as f:
            if sample.lower().startswith("key,") or sample.lower().startswith('"key"'):
                for row in csv.DictReader(f):
                    key = row.get("key") or ""
                    en = row.get("en") or row.get("text") or ""
                    if key:
                        en_map[key] = en
            else:
                for row in csv.reader(f):
                    if len(row) >= 2 and row[0]:
                        en_map[row[0]] = row[1]
    zh_map = read_two_col(ZH / "tutorial.csv", "key", "zh")
    if not zh_map and (ZH / "tutorial.csv").is_file():
        with (ZH / "tutorial.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and not row[0].lower().startswith("key"):
                    zh_map[row[0]] = row[1]
                elif len(row) >= 2 and row[0].lower() == "key":
                    continue
        # also try dict
        zh_map.update(read_two_col(ZH / "tutorial.csv", "key", "zh"))
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    for key in sorted(en_map):
        en = en_map[key]
        rid = stable_id("tutorial", key)
        item = {
            "id": rid,
            "area": "tutorial",
            "match": "key",
            "key": key,
            "context": key,
            "en": en,
            "zh": zh_map.get(key, ""),
            "status": "",
            "notes": "",
        }
        rows.append(merge_prev(item, prev, prev_en))
    return rows


def extract_glossary(prev: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    if not GLOSSARY.is_file():
        return []
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    with GLOSSARY.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            en = (row.get("en") or "").strip()
            if not en or en.startswith("#"):
                continue
            rid = stable_id("glossary", en, row.get("scope") or "")
            item = {
                "id": rid,
                "area": "glossary",
                "match": "glossary",
                "key": "",
                "context": f"scope={row.get('scope') or ''}",
                "scope": row.get("scope") or "",
                "source": row.get("source") or "",
                "en": en,
                "zh": row.get("zh") or "",
                "status": "",
                "notes": row.get("notes") or "",
            }
            rows.append(merge_prev(item, prev, prev_en))
    return rows


def extract_runtime_gaps(prev: dict[str, dict[str, str]], known_exact: set[str]) -> list[dict[str, str]]:
    dump = (
        Path(detect_game_root())
        / "AscensionGame_Data"
        / "StreamingAssets"
        / "zh-cn"
        / "untranslated.tsv"
    )
    if not dump.is_file():
        return []
    prev_en = {norm(r.get("en") or ""): r for r in prev.values()}
    rows = []
    seen: set[str] = set()
    skip_m = (
        "Promo Cards",
        "bundle",
        "Playdek account",
        "Confirmation Popup",
        "support@playdek",
        "Change resolution",
        "Share your gameplay",
        "Game Design",
        "Chief Executive",
        "Senior Product",
    )
    for line in dump.read_text(encoding="utf-8").splitlines():
        if not line.startswith("E\t"):
            continue
        text = unescape_dump(line.split("\t")[1])
        key = norm(text)
        if len(key) < 8 or key in seen or key in known_exact:
            continue
        if not re.search(r"[A-Za-z]{4,}", text):
            continue
        if any(m.lower() in text.lower() for m in skip_m) and len(text) > 200:
            # keep short UI; skip long store/credits
            if "margin-right" not in text.lower() and "honor" not in text.lower():
                continue
        seen.add(key)
        rid = stable_id("runtime", key)
        item = {
            "id": rid,
            "area": "runtime_gaps",
            "match": "exact",
            "key": "",
            "context": "untranslated.tsv",
            "en": text,
            "zh": "",
            "status": "empty",
            "notes": "运行时漏译；确认是游戏 UI 后再填",
        }
        rows.append(merge_prev(item, prev, prev_en))
    # Cap very large dumps for usability
    rows.sort(key=lambda r: -len(r.get("en") or ""))
    return rows[:800]


def summarize(name: str, rows: list[dict[str, str]]) -> dict[str, str]:
    c = Counter((r.get("status") or "empty") for r in rows)
    filled = sum(1 for r in rows if (r.get("zh") or "").strip())
    return {
        "file": name,
        "rows": str(len(rows)),
        "with_zh": str(filled),
        "empty": str(c.get("empty", 0)),
        "draft": str(c.get("draft", 0)),
        "done": str(c.get("done", 0)),
        "skip": str(c.get("skip", 0)),
    }


def main() -> None:
    WB.mkdir(parents=True, exist_ok=True)

    # Ensure rulebook en csv is fresh when possible
    try:
        from extract_rulebook import main as rb_main

        rb_main()
    except Exception as ex:
        print("extract_rulebook skipped:", ex)

    tables: list[tuple[str, list[str], list[dict[str, str]]]] = []

    rb_fields = FIELDS_COMMON + ["set", "go_name"]
    rb_prev = load_wb_csv("rulebook.csv")
    rb_rows = extract_rulebook(rb_prev)
    tables.append(("rulebook.csv", rb_fields, rb_rows))

    uk_prev = load_wb_csv("ui_keys.csv")
    uk_rows = extract_ui_keys(uk_prev)
    tables.append(("ui_keys.csv", FIELDS_COMMON, uk_rows))

    ue_prev = load_wb_csv("ui_exact.csv")
    ue_rows = extract_ui_exact(ue_prev)
    tables.append(("ui_exact.csv", FIELDS_COMMON, ue_rows))

    cl_fields = FIELDS_COMMON + ["card_id", "card_set", "field"]
    cl_prev = load_wb_csv("cards_lua.csv")
    cl_rows = extract_cards_lua(cl_prev)
    tables.append(("cards_lua.csv", cl_fields, cl_rows))

    cs_prev = load_wb_csv("cards_sheet.csv")
    cs_rows = extract_cards_sheet(cs_prev)
    tables.append(("cards_sheet.csv", FIELDS_COMMON, cs_rows))

    tu_prev = load_wb_csv("tutorial.csv")
    tu_rows = extract_tutorial(tu_prev)
    tables.append(("tutorial.csv", FIELDS_COMMON, tu_rows))

    gl_fields = FIELDS_COMMON + ["scope", "source"]
    gl_prev = load_wb_csv("glossary.csv")
    gl_rows = extract_glossary(gl_prev)
    tables.append(("glossary.csv", gl_fields, gl_rows))

    known = {norm(r["en"]) for r in rb_rows + ue_rows if r.get("en")}
    rg_prev = load_wb_csv("runtime_gaps.csv")
    rg_rows = extract_runtime_gaps(rg_prev, known)
    tables.append(("runtime_gaps.csv", FIELDS_COMMON, rg_rows))

    index_rows = []
    for name, fields, rows in tables:
        write_csv(name, rows, fields)
        index_rows.append(summarize(name, rows))
        print(f"  {name}: {len(rows)} rows, {sum(1 for r in rows if (r.get('zh') or '').strip())} with zh")

    write_csv(
        "_index.csv",
        index_rows,
        ["file", "rows", "with_zh", "empty", "draft", "done", "skip"],
    )
    print(f"wrote {WB.relative_to(ROOT)} (_index.csv + {len(tables)} tables)")


if __name__ == "__main__":
    main()
