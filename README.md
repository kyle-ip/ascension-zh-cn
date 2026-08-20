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

Most menus, card names, and effects are translated. Rulebook body text and some title art stay English. See [docs/progress.md](docs/progress.md).

The pack does not include the game, card art, or rulebook scans.

## Build

Requires [.NET 8](https://dotnet.microsoft.com/download) (or `scripts/download-tools.ps1`).

```powershell
.\scripts\publish-installer.ps1
```

Output: `dist/AscensionZhCn-Setup.exe`. String tables live in `loc/`; rebuild them with Python (`tools/build_zh.py`). Contributor notes: [docs/](docs/README.md). **Glossary (term-table) maintenance guide**: [docs/GLOSSARY.md](docs/GLOSSARY.md).

## License

MIT for tools and original translation tables. Ascension remains © Playdek / Stone Blade / respective Chinese publishers.
