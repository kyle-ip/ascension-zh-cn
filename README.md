# ascension-zh-cn

Fan Chinese language overlay for Playdek’s *Ascension: Deckbuilding Game* (Steam).

Chinese titles in use: **《创升纪元》** and **《暗杀神》**. This repo acknowledges both.

Chinese version of this README: [README.zh.md](README.zh.md)

This is **not** official DLC. It does not redistribute the game client, card art, or rulebook scans.

## Status (MVP)

- External, togglable overlay (enable / disable restores English Lua)
- Glossary locked to official/community terms (符文 / 战力 / 荣誉 …)
- Core starter + Chronicle of the Godslayer display names in `loc/zh-Hans/overrides.csv`
- Remaining cards get a **draft** effect-text pass from the glossary (needs proofreading)
- Card-face TMP CSV inside `resources.assets` and CJK fonts are **not** injected yet; in-game card art text may stay English until that lands. Combat log / Lua `display_name` / `effect_text` are what this MVP changes.

Details: [docs/feasibility-report.md](docs/feasibility-report.md)

## Requirements

- Local Steam install of Ascension
- Python 3.10+
- Close the game before enable/disable
- Writes into `AscensionGame_Data/StreamingAssets/Lua` (may need admin if the game is under `Program Files`)

## Usage

From this repo:

```powershell
python tools/extract_en.py
python tools/build_zh.py
python tools/patch.py status
python tools/patch.py enable --locale zh-Hans
python tools/patch.py disable
```

`extract_en.py` reads the install (parent folder, or `C:\Program Files (x86)\Steam\steamapps\common\Ascension`). Override with `gameRoot` in [patch.json](patch.json).

Steam **Verify integrity of game files** undoes the overlay. Run `disable` to restore from `state/backups/` without verifying.

## Layout

```text
docs/                 feasibility reports (EN default + .zh.md)
glossary/terms.csv    locked terminology + source tags
loc/en/               extracted English (generated)
loc/zh-Hans/          Simplified strings
tools/                extract / build / toggle
patch.json            enabled flag + locale
```

## Copy policy

1. Official physical Chinese (Box365 *暗杀神*, Surfin’ Meeple *创升纪元*)
2. Established community wording
3. New translation only for gaps, same glossary

Do not change Lua `card_name` identifiers.

## License

MIT for the tools and original translation tables in this repository. Ascension itself remains Playdek / Stone Blade / respective Chinese publishers’ copyright.
