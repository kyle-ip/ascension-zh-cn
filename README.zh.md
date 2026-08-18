# ascension-zh-cn

Playdek Steam 版《Ascension: Deckbuilding Game》的粉丝**简体中文**语言补丁。公开中文名只用 **《创升纪元》**。

默认英文说明：[README.md](README.md)。进度与计划：[docs/progress.zh.md](docs/progress.zh.md)。

**不是**官方 DLC，不二次分发游戏客户端、卡图或规则书扫描件。

## 玩家：一键安装 / 恢复

1. 完全退出游戏。
2. 运行 `dist\AscensionZhCn-Setup.exe`（由本仓库 `scripts/publish-installer.ps1` 生成，**不进 GitHub**）。
3. 点 **安装汉化** 或 **恢复英文**。

装在 `Program Files` 下若提示无权限，请右键「以管理员身份运行」。Steam **验证游戏完整性**会拆掉补丁，用安装器恢复即可。

`main` 和 `v*` 标签会在 GitHub Actions 上构建安装器。可从 Actions 产物下载，或打 `v1.0.0` 这样的标签，把 `AscensionZhCn-Setup.exe` 挂到 Release。exe 和 `payload` 文件夹要放在一起。

## 维护者：下载大工具（不进 Git）

BepInEx 包、便携 .NET SDK、游戏备份、字体文件体积大，已写入 `.gitignore`。在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download-tools.ps1
powershell -ExecutionPolicy Bypass -File scripts/publish-installer.ps1
```

译文迭代仍用 Python 3.10+（关游戏后再 enable）：

```powershell
python tools/extract_en.py
python tools/build_zh.py
python tools/patch.py status
python tools/patch.py enable --locale zh-Hans
python tools/patch.py disable
```

`extract_en.py` 会自动找安装目录（本仓库上一级，或默认 Steam 路径）。可在 [patch.json](patch.json) 里设置 `gameRoot`。

## 文案原则

1. 官方实体中文（方盒子早期实体、米宝海豚《创升纪元》）
2. 民间已固化译法
3. 没有来源的才按术语表新译

不要改 Lua 里作为内部 ID 的 `card_name`。游戏内公开名称不要用「暗杀神」。

## 许可

本仓库的工具和原创译表为 MIT。游戏本身版权仍归 Playdek / Stone Blade 及各中文出版社。
