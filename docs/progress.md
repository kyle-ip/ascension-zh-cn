# Status

Unofficial Simplified Chinese overlay for Steam *Ascension: Deckbuilding Game* (Unity 6000.0.58f2, IL2CPP). In-game series name: 《创升纪元》. First-set name stays 弑神编年史 (Chronicle of the Godslayer).

Chinese notes: [progress.zh.md](progress.zh.md). Install: [README](../README.md).

## Done

BepInEx 6 plugin 1.3.0 patches `GetTextByKey`, attaches YaHei as a TMP fallback, rewrites Lua `effect_text` / `flavor_text` (not `card_name`), and same-size-patches some `level1` strings. Overlay tables cover ~2600 loc keys. Leftover English is logged to `StreamingAssets/zh-cn/untranslated.tsv`.

## Not done

Title textures, rulebook body text, remaining machine-draft flavor/effects, Traditional Chinese.

Do not splice fonts into `resources.assets` or Harmony-patch `TMP_Text.set_text`. Do not write Chinese into `tutorial_EN`.

## Next

Proof `overrides.csv`, ingest the untranslated dump, then a runtime rulebook overlay. Texture titles last.
