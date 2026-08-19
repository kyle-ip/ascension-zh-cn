# ascension-zh-cn

Steam 版《Ascension: Deckbuilding Game》的非官方简体中文语言包。

[English](README.md)

## 安装

1. 从 [Releases](https://github.com/kyle-ip/ascension-zh-cn/releases) 下载 zip。
2. 解压后运行 `AscensionZhCn-Setup.exe`（与 `payload` 文件夹保持在同一目录）。
3. 选择 **安装汉化** 或 **恢复英文**。

仅支持 Windows。若游戏已在运行，请先关掉再安装。游戏在 `Program Files` 下且无法写入时，请以管理员身份运行。Steam「验证游戏文件完整性」会恢复英文。

## 现状

菜单、卡名、效果和游戏内规则书正文大部分已翻译。部分标题图仍为英文。详见 [进度](docs/progress.zh.md)。

不含游戏本体、卡图或规则书扫描件。

## 从源码开发（本仓库）

对外只保留三个入口脚本：

```powershell
.\install.ps1   # 干净环境：检查 Python、下载 BepInEx 包与便携 .NET 8 SDK（不改游戏）
.\enable.ps1    # 加载工作台译文 + 重建 overlay + 启用插件
.\disable.ps1   # 恢复英文原版
```

游戏目录两种配置方式（二选一）：

1. 在 `config.json` 填写 `gameRoot`（含 `AscensionGame.exe` 的文件夹）
2. 留空时，运行上述脚本会交互询问一次，并写回 `config.json`

新机器先跑一次 `.\install.ps1`，再关游戏后跑 `.\enable.ps1`。译表在 `loc/workbench/`（只改 `zh` 列），详见 [loc/workbench/README.zh.md](loc/workbench/README.zh.md)。

发布安装包（维护者）：先 `.\install.ps1`，再 `.\scripts\publish-installer.ps1` → `dist/AscensionZhCn-Setup.exe`。

开发说明见 [docs/](docs/README.md)。

## 许可

工具与原创译表为 MIT。游戏版权归 Playdek / Stone Blade 及各中文出版社。
