# ascension-zh-cn

Unofficial Simplified Chinese language pack for the Steam release of *Ascension: Deckbuilding Game*.

[简体中文](README.zh.md)

## Install

1. Download the zip from [Releases](https://github.com/kyle-ip/ascension-zh-cn/releases).
2. Extract it and run `AscensionZhCn-Setup.exe` (keep the `payload` folder next to the exe).
3. Choose **安装汉化** or **恢复英文**.

Windows only. Close the game first if it is already running. If the game is under `Program Files` and the installer cannot write, run it as Administrator. Steam’s “Verify integrity of game files” restores English.

In-game, the series is referred to as **《创升纪元》**.

## Status

Most menus, card names, effects, and in-game rulebook body text are translated. Some title art stays English. See [docs/progress.md](docs/progress.md).

The pack does not include the game, card art, or rulebook scans.

## Develop from this repo

Only three public entry scripts:

```powershell
.\install.ps1   # clean machine: check Python, fetch BepInEx pack + portable .NET 8 SDK (does not touch the game)
.\enable.ps1    # reload workbench translations + rebuild overlay + enable plugin
.\disable.ps1   # restore vanilla English
```

Game folder — two options:

1. Set `gameRoot` in `config.json` (folder that contains `AscensionGame.exe`)
2. Leave it empty; the scripts will ask once and write it back to `config.json`

On a new machine run `.\install.ps1` once, then close the game and run `.\enable.ps1`. Edit `zh` under `loc/workbench/`.

Maintainer release build: `.\install.ps1` then `.\scripts\publish-installer.ps1` → `dist/AscensionZhCn-Setup.exe`.

Contributor notes: [docs/](docs/README.md).

## License

MIT for tools and original translation tables. Ascension remains © Playdek / Stone Blade / respective Chinese publishers.
