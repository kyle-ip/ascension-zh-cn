# -*- coding: utf-8 -*-
"""Build / refresh loc/inventory/strings.csv from English sources + zh tables.

Inventory is the no-omission ledger: every displayable string domain must appear
here with status in {missing, draft, reviewed, waived}.

Usage:
    python tools/inventory_build.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
EN = ROOT / "loc" / "en"
OUT_DIR = ROOT / "loc" / "inventory"
OUT_CSV = OUT_DIR / "strings.csv"
OUT_SUMMARY = OUT_DIR / "summary.json"
GATES = OUT_DIR / "gates.json"

STATUSES = frozenset({"missing", "draft", "reviewed", "waived"})
CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{3,}")

# Domains that are intentionally not translated (still must be registered).
STATIC_WAIVERS: list[dict[str, str]] = [
    {
        "id": "waiver:bitmap_title",
        "domain": "bitmap_title",
        "set": "",
        "en": "(bitmap UI titles: Offline Games, Downloadable Content, set icons, …)",
        "zh": "",
        "status": "waived",
        "waived_reason": "bitmap_title",
        "source_file": "docs/architecture.zh.md",
    },
    {
        "id": "waiver:tutorial_hotspot",
        "domain": "tutorial_hotspot",
        "set": "",
        "en": "(tutorial CLICK / <link> hit-test tokens)",
        "zh": "",
        "status": "waived",
        "waived_reason": "gameplay_hit_test",
        "source_file": "plugin/AscensionZhCn/Plugin.cs",
    },
    {
        "id": "waiver:card_name_id",
        "domain": "protocol_id",
        "set": "",
        "en": "(Lua card_name internal IDs — never translate)",
        "zh": "",
        "status": "waived",
        "waived_reason": "protocol_id",
        "source_file": "StreamingAssets/Lua/*_cards.lua",
    },
]

FIELDS = [
    "id",
    "domain",
    "set",
    "en_hash",
    "en",
    "zh",
    "status",
    "waived_reason",
    "source_file",
]


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _looks_cjk(text: str) -> bool:
    return bool(CJK.search(text or ""))


def _latin_identity_name(text: str) -> bool:
    """True for intentional Latin display names (e.g. P.R.I.M.E., N.I.N.E.)."""
    t = (text or "").strip()
    if not t or _looks_cjk(t):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+\.?", t))


def _machine_mixed(zh: str) -> bool:
    """Heuristic: Chinese present plus suspicious Latin leftover (not just tags)."""
    if not zh or not _looks_cjk(zh):
        return False
    cleaned = re.sub(r"\$\{[^}]+\}", "", zh)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\b(?:ICON|LABEL|SPRITE|size|color|br)\b", "", cleaned, flags=re.I)
    words = LATIN.findall(cleaned)
    # Allow short brand tokens
    allow = {
        "Playdek",
        "Asmodee",
        "Steam",
        "Esc",
        "SBT",
        "AI",
        "DLC",
        "FAQ",
        "OK",
        "TMP",
        "Stone",
        "Blade",
        "Hedron",
        "Ferromancers",
        "Ferromancer",
        "Game",
        "Center",
        "Fate",
        "Cards",
        "Ascension",
        "Vigil",
        "Samael",
        "Deofol",
        "Kor",
        "Arha",
        "Emma",
        "Ironheart",
        "Playdek",
        "Asmodee",
        "support",
        "playdekgames",
        "com",
        "net",
        "email",
        "password",
        "CEO",
        "CTO",
        "CFO",
    }
    leftover = [w for w in words if w not in allow and w.title() not in allow]
    return len(leftover) >= 2


def _status_for(zh: str, *, source: str = "", prior: str = "") -> str:
    if prior in STATUSES and prior == "waived":
        return "waived"
    if not (zh or "").strip():
        return "missing"
    if not _looks_cjk(zh):
        # Latin-only identity names (P.R.I.M.E.) handled by forced_status.
        return "missing"
    if _machine_mixed(zh):
        return "draft"
    if source == "machine":
        return "draft"
    if source.startswith("official") or source.startswith("community"):
        return "reviewed"
    if prior == "reviewed":
        return "reviewed"
    # Phase 2: clean CJK without machine leftovers counts as reviewed
    # (UI / tutorial / rulebook rows have no machine source tag).
    return "reviewed"


def _load_prior() -> dict[str, dict[str, str]]:
    if not OUT_CSV.is_file():
        return {}
    with OUT_CSV.open(encoding="utf-8", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f) if r.get("id")}


def _add(
    rows: list[dict[str, str]],
    prior: dict[str, dict[str, str]],
    *,
    id_: str,
    domain: str,
    en: str,
    zh: str = "",
    set_: str = "",
    source_file: str = "",
    source: str = "",
    forced_status: str = "",
    waived_reason: str = "",
) -> None:
    en = en or ""
    prev = prior.get(id_, {})
    status = forced_status or _status_for(
        zh, source=source, prior=prev.get("status", "")
    )
    if status == "waived" and not waived_reason:
        waived_reason = prev.get("waived_reason") or "unspecified"
    rows.append(
        {
            "id": id_,
            "domain": domain,
            "set": set_,
            "en_hash": _hash(en) if en else "",
            "en": en.replace("\r", "\\r").replace("\n", "\\n"),
            "zh": (zh or "").replace("\r", "\\r").replace("\n", "\\n"),
            "status": status,
            "waived_reason": waived_reason,
            "source_file": source_file,
        }
    )


def _two_col(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        return []
    out: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2 or not row[0] or row[0] in {"key", "en", "id"}:
                continue
            out.append((row[0], row[1]))
    return out


def build() -> dict:
    prior = _load_prior()
    rows: list[dict[str, str]] = []

    # --- waivers ---
    for w in STATIC_WAIVERS:
        _add(
            rows,
            prior,
            id_=w["id"],
            domain=w["domain"],
            en=w["en"],
            zh=w.get("zh", ""),
            source_file=w["source_file"],
            forced_status="waived",
            waived_reason=w["waived_reason"],
        )

    # --- UI keys ---
    for key, zh in _two_col(ZH / "ui.csv"):
        _add(
            rows,
            prior,
            id_=f"ui_keys:{key}",
            domain="ui_keys",
            en=key,
            zh=zh,
            source_file="loc/zh-Hans/ui.csv",
            source="ui",
        )

    # --- tutorial ---
    for key, zh in _two_col(ZH / "tutorial.csv"):
        _add(
            rows,
            prior,
            id_=f"tutorial:{key}",
            domain="tutorial",
            en=key,
            zh=zh,
            source_file="loc/zh-Hans/tutorial.csv",
            source="tutorial",
        )

    # --- ui_runtime exact ---
    ui_rt = ZH / "ui_runtime.csv"
    if ui_rt.is_file():
        with ui_rt.open(encoding="utf-8", newline="") as f:
            for i, r in enumerate(csv.DictReader(f)):
                en = r.get("en") or ""
                zh = r.get("zh") or ""
                _add(
                    rows,
                    prior,
                    id_=f"ui_runtime:{_hash(en)}:{i}",
                    domain="ui_runtime",
                    en=en,
                    zh=zh,
                    source_file="loc/zh-Hans/ui_runtime.csv",
                )

    # --- rulebook / shop long copy ---
    rb = ZH / "rulebook.csv"
    if rb.is_file():
        with rb.open(encoding="utf-8", newline="") as f:
            for i, r in enumerate(csv.DictReader(f)):
                en = r.get("en") or ""
                zh = r.get("zh") or ""
                domain = "shop_dlc" if (
                    "bundle" in en.lower()
                    or "promo cards included" in en.lower()
                    or "<br>" in en and len(en) > 200
                ) else "rulebook_text"
                forced = ""
                reason = ""
                en_stripped = en.replace("\\n", "").replace("\\r", "").strip()
                if re.fullmatch(r"(?:<sprite=\d+>\s*)+", en_stripped or ""):
                    forced = "waived"
                    reason = "sprite_icon_only"
                elif any(
                    k in en
                    for k in (
                        "Lead Programmer",
                        "Chief Executive Officer",
                        "Additional IP Development",
                        "Administration",
                        "Game Engine Design",
                        "Lead Design",
                        "Design and Development",
                        "Justin Gary",
                        "Gary Arant",
                    )
                ):
                    # Credits pages keep Latin person names by design.
                    forced = "waived"
                    reason = "credits_names"
                _add(
                    rows,
                    prior,
                    id_=f"rulebook:{i}:{_hash(en)}",
                    domain=domain,
                    en=en,
                    zh=zh,
                    source_file="loc/zh-Hans/rulebook.csv",
                    forced_status=forced,
                    waived_reason=reason,
                )

    # --- lua cards ---
    en_flavor_by_id: dict[str, str] = {}
    en_lua = EN / "lua_cards.csv"
    if en_lua.is_file():
        with en_lua.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                cid = (r.get("id") or "").strip()
                if cid:
                    en_flavor_by_id[cid] = r.get("flavor_text") or ""

    lua = ZH / "lua_cards.csv"
    if lua.is_file():
        with lua.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                cid = r.get("id") or ""
                card_set = r.get("card_set") or ""
                src = r.get("source") or ""
                name = r.get("display_name") or ""
                effect = r.get("effect_text") or ""
                flavor = r.get("flavor_text") or ""
                en_flavor = en_flavor_by_id.get(cid, "")

                name_forced = ""
                if name.strip() and name.strip() == cid.strip() and _latin_identity_name(name):
                    name_forced = "reviewed"

                _add(
                    rows,
                    prior,
                    id_=f"cards_name:{card_set}:{cid}",
                    domain="cards_name",
                    set_=card_set,
                    en=cid,
                    zh=name,
                    source_file="loc/zh-Hans/lua_cards.csv",
                    source=src,
                    forced_status=name_forced,
                )
                _add(
                    rows,
                    prior,
                    id_=f"cards_effect:{card_set}:{cid}",
                    domain="cards_effect",
                    set_=card_set,
                    en=cid,
                    zh=effect,
                    source_file="loc/zh-Hans/lua_cards.csv",
                    source=src,
                )

                flavor_forced = ""
                flavor_reason = ""
                flavor_en = en_flavor.strip() or flavor.strip() or cid
                if not flavor.strip():
                    if not en_flavor.strip():
                        # Source has no flavor line — not a translation gap.
                        flavor_forced = "waived"
                        flavor_reason = "no_flavor_in_source"
                        flavor_en = ""
                    else:
                        flavor_en = en_flavor
                _add(
                    rows,
                    prior,
                    id_=f"cards_flavor:{card_set}:{cid}",
                    domain="cards_flavor",
                    set_=card_set,
                    en=flavor_en,
                    zh=flavor,
                    source_file="loc/zh-Hans/lua_cards.csv",
                    source=src,
                    forced_status=flavor_forced,
                    waived_reason=flavor_reason,
                )

    # --- combat log ---
    for key, zh in _two_col(ZH / "combat_log.csv"):
        _add(
            rows,
            prior,
            id_=f"combat_log:{key}",
            domain="combat_log",
            en=key,
            zh=zh,
            source_file="loc/zh-Hans/combat_log.csv",
        )

    # de-dupe by id (last wins)
    by_id = {r["id"]: r for r in rows}
    final = sorted(by_id.values(), key=lambda r: (r["domain"], r["id"]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(final)

    by_domain: dict[str, Counter] = {}
    for r in final:
        by_domain.setdefault(r["domain"], Counter())[r["status"]] += 1

    summary = {
        "total": len(final),
        "by_domain": {d: dict(c) for d, c in sorted(by_domain.items())},
        "missing_total": sum(1 for r in final if r["status"] == "missing"),
        "draft_total": sum(1 for r in final if r["status"] == "draft"),
        "reviewed_total": sum(1 for r in final if r["status"] == "reviewed"),
        "waived_total": sum(1 for r in final if r["status"] == "waived"),
    }
    OUT_SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lua_text = (ZH / "lua_cards.csv").read_text(encoding="utf-8") if (ZH / "lua_cards.csv").is_file() else ""
    forbid_hits = {"启迪": lua_text.count("启迪")}

    if not GATES.is_file():
        # Initial ceilings = current baseline (must not worsen).
        GATES.write_text(
            json.dumps(
                {
                    "phase": "T",
                    "required_domains": sorted({r["domain"] for r in final}),
                    "max_missing_by_domain": {
                        d: int(c.get("missing", 0)) for d, c in by_domain.items()
                    },
                    "max_missing_total": summary["missing_total"],
                    "forbid_glossary_terms_in_zh": ["启迪"],
                    "max_forbid_term_hits": forbid_hits,
                    "require_glossary_en": {"Enlightened": "圣贤"},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    build()
