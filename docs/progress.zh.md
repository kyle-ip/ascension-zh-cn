# 进度

Steam《Ascension: Deckbuilding Game》，Unity 6000.0.58f2（IL2CPP）。游戏内系列名《创升纪元》；首扩仍称弑神编年史。

安装见 [README.zh.md](../README.zh.md)。系统设计见 [architecture.zh.md](architecture.zh.md)。**执行计划 / 分阶段 Exit**见 [roadmap.zh.md](roadmap.zh.md)。科普介绍见 [blog-why-chinese.zh.md](blog-why-chinese.zh.md)。对照表维护见 [GLOSSARY.zh.md](GLOSSARY.zh.md)。

## 硬原则

1. **测试防回归**：仓库根执行 `python -m pytest -q`（`tests/`）；CI 同门禁。改词库/插件前先补断言。
2. **无遗漏 Inventory**：`loc/inventory/strings.csv` + `gates.json`；状态 `missing|draft|reviewed|waived`。

## 阶段状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| **T** 测试与库存地基 | **完成** | Inventory + pytest L0–L4 + CI；`gates.json` 天花板 |
| **0** 基线灌入 + 运行时热修 | **完成** | rulebook/DLC 人工稿；ui_runtime 垃圾清理；商店不卡死且长文可译（插件 **1.4.5**） |
| **1** 覆盖闭环 `missing→0` | **完成（覆盖）** | `missing_total=0`；空风味 waived；缩写卡名 reviewed；质量仍大量 draft → Phase 2 |
| **2** 按包 `draft→reviewed` | **进行中（下一步）** | 包序见 roadmap；先压 glossary「启迪」 |
| **3** UX 消闪 | 未开始 | 改插件必带回归 |

当前 Inventory 快照（`loc/inventory/summary.json`）：**total 3616**；**missing 0**；draft 2471；reviewed 244；waived 901。`gates.json` 已升到 **phase 1**（`max_missing_total: 0`）。

## 已覆盖

BepInEx 6 插件替换 `GetTextByKey`，TMP/UI `set_text` Exact/Norm，雅黑 CJK fallback。图鉴改写 Lua 展示字段（不改内部 `card_name`）。主菜单部分等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`（约 3084 keys / 2299 exact） |
| 硬编码 UI | Exact + Relocalize；短串按 glossary allow-short |
| 图鉴效果 | Lua 拼接字段已整段替换（多为 draft） |
| 规则书 / DLC 长文 | `rulebook.csv` 已灌入；运行时 Exact+Norm+分段；sprites/credits waived |
| 开关 | 安装器或 `scripts/enable.ps1` / `disable.ps1`（部署后校验 overlay 体积） |
| 对照表 | `glossary/zh-Hans.csv` SSOT |
| 回归 | `tests/` + `loc/inventory/gates.json` |

## Phase 1 已关闭的缺口

- `cards_flavor`：源无风味文案 → `waived(no_flavor_in_source)`（876）；仅有的英文风味残留已译
- `cards_name`：`P.R.I.M.E.` / `N.I.N.E.` 拉丁缩写 → `reviewed`
- `ui_runtime`：`Loading rulebook…` 坏译文已修

## 当前缺口（Phase 2）

- 卡效 / UI / 风味大量仍为 **draft**（按扩展包审校）
- glossary 禁词「启迪」仍有命中上限（目标压到 0）
- 机翻夹杂英文的卡效句子（如 “you win the game”）

## 未做（更后）

- 位图标题 — waived，专项再开
- 繁体
- 不要改 `resources.assets` 字库；不要把中文写入依赖 `CLICK`/`<link>` 的教程热区

## 变更记录（本进度文档）

| 日期 | 版本 | 更新点 |
| --- | --- | --- |
| 2026-08-22 | Phase 1 | **覆盖闭环**：`missing_total=0`；空风味 waived；缩写卡名 reviewed；修 Loading rulebook；gates 升 phase 1 |
| 2026-08-22 | Phase 2 | 术语：全表 启迪→圣贤；gates 启迪命中上限 0 |
| 2026-08-22 | v1.4.5 | **商店/规则书长文恢复**：完整 overlay 强制部署；normalize 标签→空格；长文 partial；`SetText(string)` prefix（IL2CPP 可能失败则回退 set_text）；enable 校验 overlay 体积。用户确认商店与规则书已修复。路线图落库；**Phase T/0 完成，进入 Phase 1** |
| 2026-08-22 | v1.4.4 | 恢复 `SetText(string)` + Relocalize 未激活短文案（1.4.3 覆盖回退） |
| 2026-08-22 | v1.4.3 | **商店卡死热修**：去掉全部 SetText 格式化重载 Hook；关 panelSweep；长文仅 Exact（导致长文回退，由 1.4.5 修正） |
| 2026-08-22 | v1.4.2 | ForceStateMarkers 退避；长文快路径；规则书面板扫（后证实有风险） |
| 2026-08-22 | v1.3 | 系统设计文档；Inventory + pytest；rulebook/DLC 灌入；ui_runtime 清理 |
| 2026-08-20 | v1.2 | 对照表 SSOT；ingest 规则书长文绕过机翻 |
| … | v1.1 | BepInEx 6 + IL2CPP runtime overlay 上线 |
