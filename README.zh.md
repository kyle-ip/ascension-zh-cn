# ascension-zh-cn

Steam 版《Ascension: Deckbuilding Game》的非官方简体中文语言包。

[English](README.md)

## 安装

1. 从 [Releases](https://github.com/kyle-ip/ascension-zh-cn/releases) 下载 zip。
2. 解压后运行 `AscensionZhCn-Setup.exe`（与 `payload` 文件夹保持在同一目录）。
3. 选择 **安装汉化** 或 **恢复英文**。

仅支持 Windows。若游戏已在运行，请先关掉再安装。游戏在 `Program Files` 下且无法写入时，请以管理员身份运行。Steam「验证游戏文件完整性」会恢复英文。

## 现状

菜单、卡名和效果大部分已翻译。规则书正文和部分标题图仍为英文。详见 [进度](docs/progress.zh.md)。

不含游戏本体、卡图或规则书扫描件。

## 从源码构建

需要 [.NET 8](https://dotnet.microsoft.com/download)（或先运行 `scripts/download-tools.ps1`）。

```powershell
.\scripts\publish-installer.ps1
```

产物在 `dist/AscensionZhCn-Setup.exe`。译表在 `loc/`，可用 `python tools/build_zh.py` 重建。开发说明见 [docs/](docs/README.md)。

## 许可

工具与原创译表为 MIT。游戏版权归 Playdek / Stone Blade 及各中文出版社。
