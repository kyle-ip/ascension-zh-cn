# Ascension Simplified Chinese overlay: progress and next steps

- Date: 2026-08-19
- Game: Steam *Ascension: Deckbuilding Game* (Playdek), Unity 6000.0.58f2 IL2CPP
- Public Chinese name: **《创升纪元》 only**. Keep **弑神编年史** as the Chronicle of the Godslayer *set* name.

Fan overlay. Do not ship the client, card art, or rulebook scans.

Chinese write-up (canonical for maintainers): [progress.zh.md](progress.zh.md).

## Player install

Quit the game. Run `dist\AscensionZhCn-Setup.exe` → **安装汉化** / **恢复英文**. Steam file verification undoes the overlay; use the installer to restore instead.

## What works now

BepInEx 6 IL2CPP plugin **1.3.0**: Harmony on `GetTextByKey` only; delayed YaHei TMP fallback; Lua `effect_text`/`flavor_text` rewrite (not `card_name`); same-size `level1` strings; `overlay.tsv` keys rebuilt from the runtime `Ascension_Cards` sheet (~2600+ keys). Untranslated dump: `StreamingAssets/zh-cn/untranslated.tsv`.

Do **not** Harmony-patch `TMP_Text.set_text` or splice fonts into `resources.assets`.

## Next

1. Play through leftover screens and ingest `untranslated.tsv`.
2. Proof CotG names in `overrides.csv`; machine-draft the rest.
3. Runtime rulebook overlay (too long for same-size replace).
4. Texture titles last (Offline Games, Downloadable Content, DECKBUILDING GAME).
5. Publish `AscensionZhCn-Setup.exe` as a GitHub Release; keep `dist/` and vendor SDKs gitignored.

Vendor downloads: `scripts/download-tools.ps1`. Publish the GUI: `scripts/publish-installer.ps1`.
