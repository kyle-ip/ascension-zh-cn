# Status

Unofficial Simplified Chinese overlay for Steam *Ascension: Deckbuilding Game* (Unity 6000.0.58f2, IL2CPP). In-game series name: 《创升纪元》. First-set name stays 弑神编年史 (Chronicle of the Godslayer).

Chinese notes: [progress.zh.md](progress.zh.md). Install: [README](../README.md). **Full glossary maintenance guide**: [GLOSSARY.md](GLOSSARY.md).

## Done

BepInEx 6 plugin 1.3.x patches `GetTextByKey`, attaches YaHei as a TMP fallback, rewrites Lua `effect_text` / `flavor_text` (not `card_name`), and same-size-patches some `level1` strings. Overlay tables cover **3079 loc keys / 1943 exact matches**. The glossary (Single Source of Truth) now owns **426 approved exact mappings** + **49 short-string allowances**; case-variant auto-derivation covers scope `{label,login,button,shop,ui}` so `Reward:`, `REWARD:`, `Player Name`, `PLAYER NAME` etc. all match.

Leftover English is logged to `StreamingAssets/zh-cn/untranslated.tsv`. Rulebook and DLC store paragraphs (>400 chars or containing `<sprite>` tags) are now re-routed out of the card-effect word-replacement pipeline and kept for full-sentence human translation, eliminating the mixed-language "符文为一的两main resources在Ascension" style garbage produced by previous `ingest_untranslated` runs.

## Not done

Title textures, rulebook body text (runtime overlay path is ready, awaiting human translations of rulebook.csv), remaining machine-draft flavor/effects, Traditional Chinese.

Do not splice fonts into `resources.assets` or Harmony-patch `TMP_Text.set_text`. Do not write Chinese into `tutorial_EN`.

## Next

Proof `overrides.csv`, digest the untranslated dump, then translate rulebook.csv paragraphs (15 rulebooks' What's New / Features sections plus DLC descriptions). Texture titles last.

## Changelog (this file)

| Date | Version | Delta |
| --- | --- | --- |
| 2026-08-20 | v1.2 | **Milestone:** Glossary promoted to SSOT; dual-language [GLOSSARY.md](GLOSSARY.md) + [GLOSSARY.zh.md](GLOSSARY.zh.md) maintenance guides added; `overlay.py` rewritten so glossary is loaded first and never overwritten; exact-match count grew from 925 to 1943 (+1018), fixing long-missing buttons like Confirm/Start/Close/Yes/No/Done/Undo/Bid/Pass/FAQ/or/XII. |
| 2026-08-20 | v1.2 | **Pipeline:** `ingest_untranslated.py` routes rulebook/DLC paragraphs away from `translate_effect` via `looks_rulebook_body()` heuristic; plugin now dumps strings up to 5000 chars and preserves `<sprite>` tags. |
| 2026-08-20 | v1.2 | **Cleanup:** 157 garbage machine-translation rows (e.g. `Promo兽群 #6`, `Network Connection迷失`, `Would你like以delete此friend从你的list?`) purged from `ui_runtime.csv`. |
| ...    | v1.1 | (see git log) BepInEx 6 + IL2CPP runtime overlay; Lua `effect_text` rewrite; level1 same-length patching; post-strip TMP exact matching. |
