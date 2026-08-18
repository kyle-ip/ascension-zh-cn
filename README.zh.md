# ascension-zh-cn

Playdek Steam 版《Ascension: Deckbuilding Game》的粉丝中文语言补丁。

中文名并存：**《创升纪元》**、**《暗杀神》**。本仓库两者都承认。

默认（英文）说明：[README.md](README.md)。两份不一致时以英文为准。

**不是**官方 DLC，不二次分发游戏客户端、卡图或规则书扫描件。

## 当前进度（MVP）

- 外置、可开关（enable / disable 会还原英文 Lua）
- 术语表锁定官方/民间用法（符文 / 战力 / 荣誉 …）
- 起始套 + 弑神编年史卡名在 `loc/zh-Hans/overrides.csv`
- 其余卡的效果文本是术语表**草稿**，需要校对
- 尚未注入 `resources.assets` 里的卡面 TMP CSV 和中文字体；卡图上的字可能仍是英文。本 MVP 改的是战斗日志以及 Lua 的 `display_name` / `effect_text`

详见：[docs/feasibility-report.zh.md](docs/feasibility-report.zh.md)

## 环境

- 已安装 Steam 版 Ascension
- Python 3.10+
- 开关前请先退出游戏
- 会写入 `AscensionGame_Data/StreamingAssets/Lua`（装在 `Program Files` 时可能需要管理员权限）

## 用法

在本仓库目录执行：

```powershell
python tools/extract_en.py
python tools/build_zh.py
python tools/patch.py status
python tools/patch.py enable --locale zh-Hans
python tools/patch.py disable
```

`extract_en.py` 会自动找安装目录（本仓库的上一级，或默认 Steam 路径）。可在 [patch.json](patch.json) 里设置 `gameRoot`。

Steam **验证游戏完整性**会拆掉覆盖。不想验证时，用 `disable` 从 `state/backups/` 还原。

## 文案原则

1. 官方实体中文（方盒子《暗杀神》、米宝海豚《创升纪元》）
2. 民间已固化译法
3. 没有来源的才按术语表新译

不要改 Lua 里作为内部 ID 的 `card_name`。

## 许可

本仓库的工具和原创译表为 MIT。游戏本身版权仍归 Playdek / Stone Blade 及各中文出版社。
