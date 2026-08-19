"""Load loc/workbench/*.csv into loc/zh-Hans + glossary, then rebuild overlay.tsv.

Only rows with non-empty `zh` and status != skip are applied.
"""

from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import detect_game_root  # noqa: E402

WB = ROOT / "loc" / "workbench"
ZH = ROOT / "loc" / "zh-Hans"
GLOSSARY = ROOT / "glossary" / "zh-Hans.csv"
EN = ROOT / "loc" / "en"


def norm(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_wb(name: str) -> list[dict[str, str]]:
    path = WB / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    if (row.get("status") or "").strip().lower() == "skip":
        return False
    return bool((row.get("zh") or "").strip()) and bool((row.get("en") or "").strip())


def write_dict_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def load_rulebook() -> int:
    rows_in = [r for r in read_wb("rulebook.csv") if usable(r)]
    out = []
    seen: set[str] = set()
    for r in rows_in:
        en = r["en"]
        key = norm(en)
        if key in seen:
            continue
        seen.add(key)
        ctx = r.get("context") or ""
        set_code = r.get("set") or ""
        go = r.get("go_name") or ""
        if not set_code and "set=" in ctx:
            m = re.search(r"set=([^;]+)", ctx)
            if m:
                set_code = m.group(1)
        if not go and "go=" in ctx:
            m = re.search(r"go=([^;]+)", ctx)
            if m:
                go = m.group(1)
        out.append(
            {
                "set": set_code,
                "go_name": go,
                "en": en,
                "norm": norm(en),
                "zh": r["zh"],
                "source": "workbench",
            }
        )
    write_dict_csv(
        ZH / "rulebook.csv",
        out,
        ["set", "go_name", "en", "norm", "zh", "source"],
    )
    return len(out)


def load_ui_keys() -> int:
    rows = [r for r in read_wb("ui_keys.csv") if usable(r)]
    out = [{"key": r["key"] or r.get("context") or "", "zh": r["zh"]} for r in rows if (r.get("key") or r.get("context"))]
    # keep unique by key
    merged: dict[str, str] = {}
    for row in out:
        merged[row["key"]] = row["zh"]
    write_dict_csv(ZH / "ui.csv", [{"key": k, "zh": v} for k, v in sorted(merged.items())], ["key", "zh"])
    return len(merged)


def load_ui_exact() -> int:
    rows = [r for r in read_wb("ui_exact.csv") if usable(r)]
    combat = [{"en": r["en"], "zh": r["zh"]} for r in rows if "combat" in (r.get("context") or "").lower()]
    ui = [{"en": r["en"], "zh": r["zh"]} for r in rows if "combat" not in (r.get("context") or "").lower()]
    if ui:
        write_dict_csv(ZH / "ui_runtime.csv", ui, ["en", "zh"])
    if combat:
        write_dict_csv(ZH / "combat_log.csv", combat, ["en", "zh"])
    return len(rows)


def load_cards_lua() -> int:
    rows = [r for r in read_wb("cards_lua.csv") if usable(r)]
    by_id: dict[str, dict[str, str]] = {}
    # seed from existing en for card_set
    en_meta: dict[str, str] = {}
    en_path = EN / "lua_cards.csv"
    if en_path.is_file():
        with en_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                en_meta[row.get("id") or ""] = row.get("card_set") or ""

    for r in rows:
        cid = r.get("card_id") or ""
        field = r.get("field") or ""
        if not cid or not field:
            ctx = r.get("context") or ""
            m = re.search(r"card=([^;]+)", ctx)
            if m:
                cid = m.group(1)
            m = re.search(r"field=([^;]+)", ctx)
            if m:
                field = m.group(1)
        if not cid or field not in {"display_name", "effect_text", "flavor_text"}:
            continue
        slot = by_id.setdefault(
            cid,
            {
                "id": cid,
                "card_set": en_meta.get(cid, ""),
                "display_name": "",
                "effect_text": "",
                "flavor_text": "",
                "source": "workbench",
            },
        )
        slot[field] = r["zh"]

    # Merge with previous zh file so partially filled cards keep other fields
    old_path = ZH / "lua_cards.csv"
    if old_path.is_file():
        with old_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                cid = row.get("id") or ""
                if not cid:
                    continue
                if cid not in by_id:
                    by_id[cid] = {
                        "id": cid,
                        "card_set": row.get("card_set") or en_meta.get(cid, ""),
                        "display_name": row.get("display_name") or "",
                        "effect_text": row.get("effect_text") or "",
                        "flavor_text": row.get("flavor_text") or "",
                        "source": row.get("source") or "workbench",
                    }
                else:
                    for field in ("display_name", "effect_text", "flavor_text"):
                        if not by_id[cid].get(field) and row.get(field):
                            by_id[cid][field] = row[field]

    out = [by_id[k] for k in sorted(by_id)]
    write_dict_csv(
        ZH / "lua_cards.csv",
        out,
        ["id", "card_set", "display_name", "effect_text", "flavor_text", "source"],
    )
    return len(rows)


def load_cards_sheet() -> int:
    rows = [r for r in read_wb("cards_sheet.csv") if usable(r)]
    out = []
    for r in rows:
        key = r.get("key") or r.get("context") or ""
        if key:
            out.append([key, r["zh"]])
    path = ZH / "cards.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(out)
    return len(out)


def load_tutorial() -> int:
    rows = [r for r in read_wb("tutorial.csv") if usable(r)]
    merged: dict[str, str] = {}
    for r in rows:
        key = r.get("key") or r.get("context") or ""
        if key:
            merged[key] = r["zh"]
    write_dict_csv(
        ZH / "tutorial.csv",
        [{"key": k, "zh": v} for k, v in sorted(merged.items())],
        ["key", "zh"],
    )
    return len(merged)


def load_glossary() -> int:
    rows = [r for r in read_wb("glossary.csv") if usable(r)]
    # Preserve comment lines from original
    comments: list[list[str]] = []
    old_rows: list[dict[str, str]] = []
    if GLOSSARY.is_file():
        with GLOSSARY.open(encoding="utf-8-sig", newline="") as f:
            raw = f.read().splitlines()
        # Keep header + #-comment data rows if DictReader skipped them
        with GLOSSARY.open(encoding="utf-8-sig", newline="") as f:
            old_rows = list(csv.DictReader(f))

    by_en: dict[str, dict[str, str]] = {}
    for row in old_rows:
        en = (row.get("en") or "").strip()
        if en and not en.startswith("#"):
            by_en[en] = row

    for r in rows:
        en = (r.get("en") or "").strip()
        if not en:
            continue
        scope = r.get("scope") or ""
        if not scope and "scope=" in (r.get("context") or ""):
            m = re.search(r"scope=([^;]*)", r["context"])
            if m:
                scope = m.group(1)
        by_en[en] = {
            "en": en,
            "zh": r["zh"],
            "scope": scope,
            "source": r.get("source") or "workbench",
            "notes": r.get("notes") or "",
        }

    out = list(by_en.values())
    write_dict_csv(GLOSSARY, out, ["en", "zh", "scope", "source", "notes"])
    return len(rows)


def load_runtime_gaps() -> int:
    """Merge filled runtime gaps into ui_runtime.csv (Exact overlay)."""
    rows = [r for r in read_wb("runtime_gaps.csv") if usable(r)]
    if not rows:
        return 0
    path = ZH / "ui_runtime.csv"
    by_norm: dict[str, tuple[str, str]] = {}
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                en = row.get("en") or ""
                zh = row.get("zh") or ""
                if en and zh:
                    by_norm[norm(en)] = (en, zh)
    for r in rows:
        by_norm[norm(r["en"])] = (r["en"], r["zh"])
    write_dict_csv(
        path,
        [{"en": en, "zh": zh} for en, zh in by_norm.values()],
        ["en", "zh"],
    )
    return len(rows)


def deploy_overlay() -> None:
    src = ZH / "overlay.tsv"
    if not src.is_file():
        return
    game = Path(detect_game_root())
    dest = game / "AscensionGame_Data" / "StreamingAssets" / "zh-cn" / "overlay.tsv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"deployed {dest}")


def main() -> None:
    if not WB.is_dir():
        raise SystemExit(f"missing {WB}; run tools/workbench_extract.py first")

    counts = {
        "rulebook": load_rulebook(),
        "ui_keys": load_ui_keys(),
        "ui_exact": load_ui_exact(),
        "cards_lua": load_cards_lua(),
        "cards_sheet": load_cards_sheet(),
        "tutorial": load_tutorial(),
        "glossary": load_glossary(),
        "runtime_gaps": load_runtime_gaps(),
    }
    for k, v in counts.items():
        print(f"  loaded {k}: {v}")

    # sync glossary terms.csv used by older tools
    try:
        from sync_glossary import main as sync_main

        sync_main()
    except Exception as ex:
        print("sync_glossary:", ex)

    from overlay import write_overlay

    # Keep achievements Exact map next to other zh-Hans tables when present.
    ach_wb = WB / "achievements.csv"
    ach_zh = ZH / "achievements.csv"
    if ach_wb.is_file():
        shutil.copy2(ach_wb, ach_zh)
        print(f"  copied achievements: {ach_wb.name}")

    out = write_overlay(ZH / "overlay.tsv")
    print(f"overlay -> {out}")
    try:
        deploy_overlay()
    except Exception as ex:
        print("deploy overlay failed (close game?):", ex)

    print("done. Restart the game to see changes.")
    print("Tip: daily use is .\\enable.ps1 / .\\disable.ps1 at the repo root.")


if __name__ == "__main__":
    main()
