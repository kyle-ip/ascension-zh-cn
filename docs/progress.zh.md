# 进度

Steam《Ascension: Deckbuilding Game》，Unity 6000.0.58f2（IL2CPP）。游戏内系列名《创升纪元》；首扩仍称弑神编年史。

安装见 [README.zh.md](../README.zh.md)。

## 已覆盖

BepInEx 6 插件（1.4.1）在运行时替换 `GetTextByKey`，延迟挂载雅黑作为 TMP 回退，并在打开规则书时扫 TMP。图鉴改写 Lua `effect_text` / `flavor_text`（不改 `card_name`）。主菜单部分文案在 `level1` 里等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`，约 3000+ 键（含 Legends） |
| 硬编码 UI | 精确匹配 + 定时扫描 TMP |
| 图鉴效果 | Lua 拼接字段已整段替换 |
| 规则书正文 | 15 扩展 TMP 已重抽并译入 `rulebook.csv`（约 359 条唯一）；空白折叠 Exact + Auto Size |
| 开关 | 仓库根目录仅三个入口：`.\install.ps1` / `.\enable.ps1` / `.\disable.ps1`；游戏路径见 `config.json` |

## 译文工作台（推荐流程）

分区配置在 [`loc/workbench/`](../loc/workbench/README.zh.md)：

1. 新机器先 `.\install.ps1`（只装依赖；`config.json` 未填会询问游戏目录）
2. 你只改各表 **`zh` 列**（Excel 请存 UTF-8）
3. `.\enable.ps1` — 加载工作台、重建 overlay、部署插件

当前索引见 `loc/workbench/_index.csv`（规则书/UI/卡牌/教程等多数已有草稿中文；`runtime_gaps.csv` 为运行时仍英文、待你确认后填写）。

## 未做

- 位图标题与扩展缩写图标
- 规则书**截图贴图**里的英文按钮/牌名（PLAY ALL、中央列等）
- 官方印刷/PDF 规则书视觉汉化（下期）
- 部分效果 / 风味仍是机器稿
- 商店 Bundle / 制作人员名单（非规则书页）
- 繁体
