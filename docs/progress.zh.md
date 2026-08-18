# 进度

Steam《Ascension: Deckbuilding Game》，Unity 6000.0.58f2（IL2CPP）。游戏内系列名《创升纪元》；首扩仍称弑神编年史。

安装见 [README.zh.md](../README.zh.md)。

## 已覆盖

BepInEx 6 插件（1.3.0）在运行时替换 `GetTextByKey`，并延迟挂载雅黑作为 TMP 回退。图鉴改写 Lua `effect_text` / `flavor_text`（不改 `card_name`）。主菜单部分文案在 `level1` 里等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`，约 2600+ 键（含 Legends） |
| 硬编码 UI | 精确匹配 + 定时扫描 TMP |
| 图鉴效果 | Lua 拼接字段已整段替换 |
| 开关 | 安装器或 `python tools/patch.py enable\|disable` |

漏译会记到 `StreamingAssets/zh-cn/untranslated.tsv`，随后可 `python tools/ingest_untranslated.py`。

术语：符文 / 战力 / 荣誉；获取 / 击败 / 放逐；学徒 / 民兵 / 秘教士 / 重装步兵 / 邪教徒；神器（Construct）；启迪 / 生命 / 机械 / 虚空。

## 未做

- 位图标题（Offline Games、Downloadable Content、DECKBUILDING GAME、扩展缩写图标）
- 规则书正文（packed 英文过长，需单独 overlay）
- 部分效果 / 风味仍是机器稿
- 繁体

不要改 `resources.assets` 里的 TMP 字库，也不要对 `TMP_Text.set_text` 打 Harmony（会损坏资源或白屏）。不要把中文写入 `tutorial_EN`。

## 后续

校对 `overrides.csv` 与机器稿 → 消化漏译表 → 规则书运行时 overlay → 位图标题最后再考虑。
