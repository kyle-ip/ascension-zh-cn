"""Bake rulebook Chinese into Rulebook* prefab TMP blobs in resources.assets.

TMP m_text is not in the IL2CPP TypeTree (only m_Name etc.), so this rewrites
length-prefixed UTF-8 inside MonoBehaviour raw data and lets UnityPy update
object sizes. Same-size hex replace cannot work: Chinese is usually longer.

Runtime CJK font is still required. Bitmap screenshots stay English.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from common import BACKUP_DIR, detect_game_root, resources_assets  # noqa: E402
from extract_rulebook import SKIP_GO, children_of_transform, deref, go_name, transform_of_go  # noqa: E402

ZH_RB = ROOT / "loc" / "zh-Hans" / "rulebook.csv"


def collapse(value: str) -> str:
    if not value:
        return value
    s = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    s = re.sub(r" *\n *", "\n", s)
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s.strip()


def load_zh() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with ZH_RB.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            zh = (row.get("zh") or "").strip()
            en = row.get("en") or ""
            norm = row.get("norm") or ""
            if not zh or not en or en == zh:
                continue
            mapping[en] = zh
            mapping[en.replace("\r\n", "\n").replace("\r", "\n")] = zh
            if norm:
                mapping[norm] = zh
            collapsed = collapse(en)
            if collapsed:
                mapping[collapsed] = zh
    return mapping


def lookup(text: str, mapping: dict[str, str]) -> str | None:
    zh = mapping.get(text)
    if zh and zh != text:
        return zh
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    if unified != text:
        zh = mapping.get(unified)
        if zh and zh != unified:
            return zh
    c = collapse(text)
    if c and c != text:
        zh = mapping.get(c)
        if zh and zh != c:
            return zh
    return None


def aligned_span(ln: int) -> int:
    return (ln + 3) & ~3


def replace_strings(raw: bytes, mapping: dict[str, str]) -> tuple[bytes, int]:
    out = bytearray()
    i = 0
    n = len(raw)
    last = 0
    changed = 0
    while i + 4 <= n:
        ln = int.from_bytes(raw[i : i + 4], "little")
        if 2 <= ln <= 12000 and i + 4 + ln <= n:
            chunk = raw[i + 4 : i + 4 + ln]
            if all(b in (9, 10, 13) or 32 <= b < 127 or b >= 0x80 for b in chunk):
                try:
                    text = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    span = aligned_span(ln)
                    zh = lookup(text, mapping)
                    if zh:
                        out.extend(raw[last:i])
                        payload = zh.encode("utf-8")
                        new_ln = len(payload)
                        new_span = aligned_span(new_ln)
                        out.extend(new_ln.to_bytes(4, "little"))
                        out.extend(payload)
                        out.extend(b"\x00" * (new_span - new_ln))
                        last = i + 4 + span
                        i = last
                        changed += 1
                        continue
                    i += 4 + span
                    continue
        i += 1
    out.extend(raw[last:])
    return bytes(out), changed


def walk_mb(env, root_go):
    objs = {o.path_id: o for o in env.objects}
    tr = transform_of_go(objs, root_go)
    if not tr:
        return
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
            try:
                data = go.read()
                for pair in data.m_Component:
                    c = deref(objs, pair.component)
                    if c and c.type.name == "MonoBehaviour":
                        yield c
            except Exception:
                pass
        q.extend(children_of_transform(objs, t))


def apply(dry_run: bool = False) -> int:
    if not ZH_RB.is_file():
        raise FileNotFoundError(ZH_RB)
    mapping = load_zh()
    game = detect_game_root()
    live = resources_assets(game)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / "resources.assets"
    if not backup.is_file():
        shutil.copy2(live, backup)
        print(f"backed up resources.assets -> {backup}")

    import UnityPy

    env = UnityPy.load(str(live))
    roots = []
    for obj in env.objects:
        if obj.type.name != "GameObject":
            continue
        name = go_name(obj)
        if name.startswith("Rulebook") and name not in SKIP_GO:
            roots.append((name, obj))

    patched_objs = 0
    patched_strings = 0
    for root_name, go in sorted(roots, key=lambda x: x[0]):
        root_hits = 0
        seen_mb: set[int] = set()
        for mb in walk_mb(env, go):
            if mb.path_id in seen_mb:
                continue
            seen_mb.add(mb.path_id)
            raw = bytes(mb.get_raw_data())
            new_raw, hits = replace_strings(raw, mapping)
            if hits and new_raw != raw:
                if not dry_run:
                    mb.set_raw_data(new_raw)
                patched_objs += 1
                patched_strings += hits
                root_hits += hits
        print(f"  {root_name}: {root_hits} strings")

    print(f"{'dry-run' if dry_run else 'patched'} {patched_strings} strings in {patched_objs} MonoBehaviours")
    if dry_run or patched_objs == 0:
        return patched_strings
    out_dir = BACKUP_DIR / "rulebook_out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    env.save(out_path=str(out_dir))
    written = next(out_dir.glob("resources.assets*"))
    shutil.copy2(written, live)
    print(f"saved {live} ({live.stat().st_size} bytes)")
    return patched_strings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
