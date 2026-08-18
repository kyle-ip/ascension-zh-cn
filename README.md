# ascension-zh-cn

Fan Simplified Chinese overlay for Playdek’s *Ascension: Deckbuilding Game* (Steam).

Public in-game name: **《创升纪元》 only**. Progress and next steps: [docs/progress.md](docs/progress.md). Chinese README: [README.zh.md](README.zh.md).

This is **not** official DLC. It does not redistribute the game client, card art, or rulebook scans.

## Players

Quit the game, then run `dist\AscensionZhCn-Setup.exe` (produced by `scripts/publish-installer.ps1`; the exe is gitignored). Click **安装汉化** or **恢复英文**.

Steam **Verify integrity of game files** undoes the overlay. Use the installer to restore instead.

CI on `main` and `v*` tags builds the installer with GitHub Actions (`windows-latest`, .NET 8). Download the artifact from the Actions run, or push a tag like `v1.0.0` to attach `AscensionZhCn-Setup.exe` to a GitHub Release. Keep the `payload` folder next to the exe.

## Maintainers

Large vendor files (BepInEx zip, portable .NET SDK, font binaries, game backups) stay off GitHub:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download-tools.ps1
powershell -ExecutionPolicy Bypass -File scripts/publish-installer.ps1
```

Python 3.10+ remains the translation pipeline (close the game first):

```powershell
python tools/extract_en.py
python tools/build_zh.py
python tools/patch.py status
python tools/patch.py enable --locale zh-Hans
python tools/patch.py disable
```

`extract_en.py` reads the install (parent folder, or the default Steam path). Override with `gameRoot` in [patch.json](patch.json).

## Layout

```text
docs/                 progress + feasibility (EN default + .zh.md)
glossary/terms.csv    locked terminology + source tags
loc/en/               extracted English (generated)
loc/zh-Hans/          Simplified strings
installer/            Windows install/restore GUI (source)
scripts/              download vendor tools; publish the GUI
tools/                extract / build / toggle (maintainers)
patch.json            enabled flag + locale
```

## Copy policy

1. Official physical Chinese (Box365 *暗杀神*, Surfin’ Meeple *创升纪元*)
2. Established community wording
3. New translation only for gaps, same glossary

Do not change Lua `card_name` identifiers.

## License

MIT for the tools and original translation tables in this repository. Ascension itself remains Playdek / Stone Blade / respective Chinese publishers’ copyright.
