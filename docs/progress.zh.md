# 进度

Steam《Ascension: Deckbuilding Game》，Unity 6000.0.58f2（IL2CPP）。游戏内系列名《创升纪元》；首扩仍称弑神编年史。

安装见 [README.zh.md](../README.zh.md)。系统设计见 [architecture.zh.md](architecture.zh.md)。科普介绍见 [blog-why-chinese.zh.md](blog-why-chinese.zh.md)。完整对照表维护指南见 [GLOSSARY.zh.md](GLOSSARY.zh.md)。

## 硬原则

1. **测试防回归**：在仓库根执行 `python -m pytest -q`（见 `tests/`）；CI 同门禁。改词库/插件前先补断言。
2. **无遗漏 Inventory**：`loc/inventory/strings.csv` + `gates.json`；状态 `missing|draft|reviewed|waived`。

## 已覆盖

BepInEx 6 插件在运行时替换 `GetTextByKey`，并延迟挂载雅黑作为 TMP 回退。图鉴改写 Lua `effect_text` / `flavor_text`（不改 `card_name`）。主菜单部分文案在 `level1` 里等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`（约 3084 keys / 2290 exact） |
| 硬编码 UI | 精确匹配 + 定时扫描 TMP；短字符串按 glossary allow-short |
| 图鉴效果 | Lua 拼接字段已整段替换（仍有机翻 draft） |
| 规则书文字段 / DLC 长文 | `rulebook.csv` 已灌入人工稿（Phase 0）；sprites/credits 为 waived |
| 开关 | 安装器或 `python tools/patch.py enable\|disable` |
| 对照表 | `glossary/zh-Hans.csv` SSOT |
| 回归 | `tests/` + `loc/inventory/gates.json` 天花板 |

## 未做 / 进行中

- Phase 1：卡效纯英文 Lua 残留、ui_runtime 余下机翻、Inventory `missing`（主要是空风味）清零
- Phase 2：按扩展包把 `draft` → `reviewed`；启迪→圣贤等术语强制回写
- Phase 3：消闪（字体/L2 时序、扩大 L1）
- 位图标题（Offline Games 等）— waived，专项再开
- 繁体

不要改 `resources.assets` 里的 TMP 字库。不要把中文写入依赖 `CLICK`/`<link>` 的教程热区。

## 后续

消化 Inventory missing → 术语门禁压低「启迪」→ 按包审校 → UX 消闪。

## 变更记录（本进度文档）

| 日期 | 版本 | 更新点 |
| --- | --- | --- |
| 2026-08-22 | v1.4.2 | **性能热修**：ForceStateMarkers 空扫描指数退避（此前每秒全场景扫描导致商店卡死）；长文只走 Exact/归一化；规则书面板定点扫 + SetText postfix；默认关闭诊断写盘 |
| 2026-08-22 | v1.4.1 | overlay `\r` 双重转义修复；DumpLongStrings 默认关 |
| 2026-08-22 | v1.3 | 新增系统设计文档；Inventory + pytest 门禁；rulebook/DLC 人工稿灌入；ui_runtime 关键垃圾清理 |
| 2026-08-20 | v1.2 | 对照表升级为 SSOT；ingest 规则书长文绕过机翻 |
| … | v1.1 | BepInEx 6 + IL2CPP runtime overlay 上线 |
