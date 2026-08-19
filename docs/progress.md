# Status

Unofficial Simplified Chinese overlay for Steam *Ascension: Deckbuilding Game* (Unity 6000.0.58f2, IL2CPP). In-game series name: 《创升纪元》. First-set name stays 弑神编年史 (Chronicle of the Godslayer).

Chinese notes: [progress.zh.md](progress.zh.md). Install: [README](../README.md).

## Done

BepInEx 6 plugin **1.4.1** patches `GetTextByKey`, attaches YaHei as a TMP fallback, rewrites Lua `effect_text` / `flavor_text` (not `card_name`), same-size-patches some `level1` strings, and overlays in-game rulebook TMP via `loc/zh-Hans/rulebook.csv` (~310 strings) with collapsed-whitespace Exact matching and rulebook Auto Size. Overlay tables cover ~3000 loc keys. Leftover English is logged to `StreamingAssets/zh-cn/untranslated.tsv` (long-string dump limit 4000).

Rulebook pipeline: `tools/extract_rulebook.py` → `tools/build_rulebook_zh.py` → `tools/overlay.py`. Glossary edits: update `glossary/zh-Hans.csv`, then `python tools/sync_glossary.py`. Audit: [rulebook_audit_2026-08-19.md](rulebook_audit_2026-08-19.md).

## Not done

Title textures, baked rulebook screenshot English (PLAY ALL / center-row names), official printed/PDF rulebook art (next phase), remaining machine-draft flavor/effects, Traditional Chinese.

Do not splice fonts into `resources.assets` or Harmony-patch `TMP_Text.set_text`. Do not write Chinese into `tutorial_EN`.

## Next

Proof `overrides.csv`, ingest the untranslated dump, in-game page-through of each expansion rulebook, texture titles last.
