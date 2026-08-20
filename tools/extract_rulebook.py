"""List TMP_Text component paths in each RulebookXX prefab.

UnityPy can resolve GameObject names and the prefab hierarchy in
``resources.assets``, but IL2CPP builds omit the MonoBehaviour TypeTree, so
``m_text`` field values cannot be read here. This script still produces a
manifest: for every RulebookXX prefab, list the GameObject path of every
TMP Text / TMP Title / TMP Body Text / WhatsNew / Rules Text / Flavor Text
component. That tells the operator what the relaxed plugin dump
(``DumpLongStrings=true``) should capture when each rulebook is opened.

Usage::

    python tools/extract_rulebook.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import UnityPy  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from common import detect_game_root, resources_assets  # noqa: E402

OUT = ROOT / "loc" / "en" / "rulebook_manifest.csv"

# All 16 RulebookXX prefabs found in resources.assets via _unitypy_diag.py.
RULEBOOK_PREFABS = (
    "RulebookASCL",
    "RulebookCotG",
    "RulebookRotF",
    "RulebookSoS",
    "RulebookIH",
    "RulebookRoV",
    "RulebookDU",
    "RulebookDoC",
    "RulebookDS",
    "RulebookWoS",
    "RulebookGotE",
    "RulebookVotA",
    "RulebookDLV",
    "RulebookDLRM",
    "Rulebook",
)

# GameObject names that carry rulebook text. Matches the names found in
# RulebookDU's hierarchy (see _unitypy_diag4.py output).
TEXT_OBJECT_NAMES = {
    "TMP Text",
    "TMP Title",
    "TMP Body Text",
    "TMP Class Text",
    "TMP Flavor Text",
    "TMP VP Text",
    "TMP Cardset Text",
    "TMP Energize Text",
    "TMP Rules Text",
    "TMP Cost",
    "TMP Fate Text",
    "TMP Ability01 Text",
    "TMP Ability02 Text",
    "TMP Ability03 Text",
    "TMP Ability04 Text",
    "TMP Ability05 Text",
    "TMP Ability06 Text",
    "TMP Ability07 Text",
    "TMP Ability08 Text",
    "TMP Ability09 Text",
    "TMP Ability10 Text",
    "TMP SubMeshUI [TextMeshPro/Sprite]",
    "WhatsNew",
    "RulesFlavor",
}


def resolve(pptr, by_pid):
    pid = getattr(pptr, "m_PathID", None)
    if pid is None and isinstance(pptr, (list, tuple)) and len(pptr) >= 2:
        pid = pptr[1]
    if pid is None:
        return None
    return by_pid.get(pid)


def walk_gameobject(go_obj, by_pid, depth=0, max_depth=12):
    """Yield (depth, path, gameobject) for the prefab subtree.

    `path` is a "/"-joined string of GameObject names from the root.
    """
    if depth > max_depth:
        return
    try:
        go_data = go_obj.read()
    except Exception:
        return
    name = getattr(go_data, "m_Name", "") or ""
    yield depth, name, go_obj

    comps = getattr(go_data, "m_Component", []) or []
    transform_obj = None
    for c in comps:
        comp_obj = resolve(c.component, by_pid)
        if comp_obj is None:
            continue
        if comp_obj.type.name in ("RectTransform", "Transform"):
            transform_obj = comp_obj
            break
    if transform_obj is None:
        return
    try:
        t_data = transform_obj.read()
    except Exception:
        return
    children = getattr(t_data, "m_Children", []) or []
    for child_ptr in children:
        child_t = resolve(child_ptr, by_pid)
        if child_t is None:
            continue
        try:
            child_go = resolve(getattr(child_t.read(), "m_GameObject", None), by_pid)
        except Exception:
            child_go = None
        if child_go is None:
            continue
        yield from walk_gameobject(child_go, by_pid, depth + 1, max_depth)


def find_text_components(go_obj, by_pid):
    """Return list of (component_type, ) for MonoBehaviour comps whose
    GameObject name suggests it carries text."""
    try:
        go_data = go_obj.read()
    except Exception:
        return []
    name = getattr(go_data, "m_Name", "") or ""
    if name not in TEXT_OBJECT_NAMES:
        return []
    out = []
    comps = getattr(go_data, "m_Component", []) or []
    for c in comps:
        comp_obj = resolve(c.component, by_pid)
        if comp_obj is None:
            continue
        ctype = comp_obj.type.name
        if ctype == "MonoBehaviour":
            out.append(ctype)
    return out


def find_prefab_root(env, prefab_name: str, by_pid):
    for obj in env.objects:
        if obj.type.name != "GameObject":
            continue
        try:
            d = obj.read()
            if getattr(d, "m_Name", "") == prefab_name:
                return obj
        except Exception:
            continue
    return None


def extract_manifest(env, prefab_name: str, by_pid) -> list[tuple[str, str, str]]:
    """Return list of (prefab, path, component_name) rows for text-bearing
    GameObjects in the named prefab."""
    rows: list[tuple[str, str, str]] = []
    root = find_prefab_root(env, prefab_name, by_pid)
    if root is None:
        return rows
    path_parts: list[str] = []
    for depth, name, go_obj in walk_gameobject(root, by_pid):
        # Trim path_parts to current depth
        while len(path_parts) > depth:
            path_parts.pop()
        path_parts.append(name)
        path = "/".join(path_parts)
        # Check if this GameObject carries text
        if name in TEXT_OBJECT_NAMES:
            rows.append((prefab_name, path, name))
    return rows


def main() -> int:
    game = detect_game_root()
    assets_path = resources_assets(game)
    print(f"loading {assets_path}")
    if not assets_path.is_file():
        print(f"missing: {assets_path}")
        return 1

    try:
        env = UnityPy.load(str(assets_path))
    except Exception as ex:
        print(f"UnityPy.load failed: {ex}")
        return 2

    by_pid = {obj.path_id: obj for obj in env.objects}

    all_rows: list[tuple[str, str, str]] = []
    for prefab in RULEBOOK_PREFABS:
        rows = extract_manifest(env, prefab, by_pid)
        print(f"  {prefab}: {len(rows)} text objects")
        all_rows.extend(rows)

    if not all_rows:
        print("\nno text objects found; prefab list may be wrong.")
        return 3

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prefab", "path", "component"])
        for prefab, path, comp in all_rows:
            w.writerow([prefab, path, comp])
    print(f"\nwrote {OUT} ({len(all_rows)} rows)")
    print(
        "NOTE: this is a manifest only. The actual English text comes from\n"
        "  the plugin's relaxed long-string dump (Plugin.cs DumpLongStrings=true,\n"
        "  kind 'L' entries in untranslated.tsv). After playing the game and\n"
        "  opening each rulebook, run:\n"
        "    python tools/ingest_untranslated.py\n"
        "  to merge captured strings into loc/zh-Hans/rulebook.csv."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
