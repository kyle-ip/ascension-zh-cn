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
| **1** 覆盖闭环 `missing→0` | **完成** | `missing_total=0`；空风味 waived；缩写卡名 reviewed |
| **2** 按包 `draft→reviewed` | **完成** | 全包 effect/name/UI 审校；`draft_total=0`；启迪=0；credits waived |
| **3** UX 消闪 | **实施完成（待 L6）** | 插件 **1.5.0**：onPreRender 状态标记、L1 Exact 回退、规则书面板定向刷新；清单见 docs/l6-checklist.zh.md |

当前 Inventory 快照（`loc/inventory/summary.json`）：**total 3616**；**missing 0**；**draft 0**；reviewed 2712；waived 904。`gates.json` 已升到 **phase 3**（覆盖/草稿天花板仍为 0；消闪门禁见 pytest `test_phase3_antiflicker`）。

## 已覆盖

BepInEx 6 插件替换 `GetTextByKey`，TMP/UI `set_text` Exact/Norm，雅黑 CJK fallback。图鉴改写 Lua 展示字段（不改内部 `card_name`）。主菜单部分等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`（约 3084 keys / 2299 exact） |
| 硬编码 UI | Exact + Relocalize；短串按 glossary allow-short |
| 图鉴效果 | Lua 展示字段整段中文；`source` 无 machine |
| 规则书 / DLC 长文 | `rulebook.csv`；运行时 Exact+Norm+分段；sprites/credits waived |
| 开关 | 安装器或 `scripts/enable.ps1` / `disable.ps1`（部署后校验 overlay 体积） |
| 对照表 | `glossary/zh-Hans.csv` SSOT |
| 回归 | `tests/` + `loc/inventory/gates.json` |

## Phase 2 已关闭

- 全扩展包卡效 / 卡名 → `reviewed`（938+938）
- 有源风味 → 译后 `reviewed`；无源风味 → `waived(no_flavor_in_source)`
- UI / tutorial / combat_log / shop_dlc → `reviewed`
- 规则书 credits（人名保留拉丁）→ `waived(credits_names)`
- glossary：Enlightened→圣贤；禁词「启迪」命中 = 0
- `lua_cards.csv`：无 `machine` source；center deck → 中央牌库
- gates：`phase=2`，`max_draft_total=0` + 分域 draft 天花板

## Phase 3 已落地（代码）

- 同步 CJK fallback 后再 `_ready` / 挂 L2（既有）
- `Camera.onPreRender` + LateUpdate 双保险强制状态标记中文
- `LocPostfix`：Keys 未命中时 Exact/Norm 回退（扩大有效 L1）
- 场景加载与周期调度：`RelocalizeKnownPanels`（仅规则书根，不含商店）
- 对局场景加快状态标记扫描；原生 CH：暂缓（无官方 zh-Hans 包）
- L6 人工清单：`docs/l6-checklist.zh.md`（冷启动勾选后才算 Exit）

## 未做（更后）

- L6 人工勾选签收
- 位图标题 — waived，专项再开
- 繁体
- 不要改 `resources.assets` 字库；不要把中文写入依赖 `CLICK`/`<link>` 的教程热区

## 变更记录（本进度文档）

| 日期 | 版本 | 更新点 |
| --- | --- | --- |
| 2026-08-22 | Phase 3 / 1.5.0 | **消闪实施**：onPreRender 状态标记；L1 Exact 回退；规则书面板定向刷新；L6 清单；gates phase 3 |
| 2026-08-22 | Phase 2 | **质量闭环**：`draft_total=0`；全包 reviewed；启迪=0；credits waived；gates phase 2 + draft 天花板；pytest 25 |
| 2026-08-22 | Phase 1 | **覆盖闭环**：`missing_total=0`；空风味 waived；缩写卡名 reviewed；修 Loading rulebook；gates 升 phase 1 |
| 2026-08-22 | Phase 2 kickoff | 术语：全表 启迪→圣贤；gates 启迪命中上限 0 |
| 2026-08-22 | v1.4.5 | **商店/规则书长文恢复**：完整 overlay 强制部署；normalize 标签→空格；长文 partial；`SetText(string)` prefix；enable 校验 overlay 体积 |
| 2026-08-22 | v1.4.4 | 恢复 `SetText(string)` + Relocalize 未激活短文案（1.4.3 覆盖回退） |
| 2026-08-22 | v1.4.3 | **商店卡死热修**：去掉全部 SetText 格式化重载 Hook；关 panelSweep |
| 2026-08-22 | v1.4.2 | ForceStateMarkers 退避；长文快路径；规则书面板扫（后证实有风险） |
| 2026-08-22 | v1.3 | 系统设计文档；Inventory + pytest；rulebook/DLC 灌入；ui_runtime 清理 |
| 2026-08-20 | v1.2 | 对照表 SSOT；ingest 规则书长文绕过机翻 |
| … | v1.1 | BepInEx 6 + IL2CPP runtime overlay 上线 |
