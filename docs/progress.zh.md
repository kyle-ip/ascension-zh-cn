# 进度

Steam《Ascension: Deckbuilding Game》，Unity 6000.0.58f2（IL2CPP）。游戏内系列名《创升纪元》；首扩仍称弑神编年史。

安装见 [README.zh.md](../README.zh.md)。完整对照表维护指南见 [docs/GLOSSARY.zh.md](GLOSSARY.zh.md)。

## 已覆盖

BepInEx 6 插件（1.3.x）在运行时替换 `GetTextByKey`，并延迟挂载雅黑作为 TMP 回退。图鉴改写 Lua `effect_text` / `flavor_text`（不改 `card_name`）。主菜单部分文案在 `level1` 里等长替换。

| 范围 | 说明 |
| --- | --- |
| 卡面 / 菜单 loc | `overlay.tsv`，约 3079 键 / 1943 exact（含 Legends），其中 **426 条 exact 直接来源于 glossary SSOT** |
| 硬编码 UI | 精确匹配 + 定时扫描 TMP；短字符串（≤4 字符）按 glossary allow-short 放行 |
| 图鉴效果 | Lua 拼接字段已整段替换 |
| 开关 | 安装器或 `python tools/patch.py enable\|disable` |
| 对照表 | 见 [glossary/zh-Hans.csv](../glossary/zh-Hans.csv)，458 行（scope 20 类 / 19 种来源）；构建后推导 426 条 exact + 49 条 short |
| 大小写变体 | `label/login/button/shop/ui` 5 类 scope 自动生成 ALLCAPS/alllower/Capitalized 三种 exact key；解决 Reward:/REWARD:、Player Name/PLAYER NAME 漏匹配 |

漏译会记到 `StreamingAssets/zh-cn/untranslated.tsv`，随后可 `python tools/ingest_untranslated.py`。规则书段/DLC 长段（>400 字符 或 含 `<sprite>`）现在会绕过 `translate_effect`，进入 `rulebook.csv` 留空等待人工翻译，**不会再产生中英混杂机翻垃圾**。

## 未做

- 位图标题（Offline Games、Downloadable Content、DECKBUILDING GAME、扩展缩写图标）
- 规则书正文（运行时 overlay 路径已打通，待完成 rulebook.csv 内各段人工翻译）
- 部分效果 / 风味仍是机器稿（可逐条补 glossary 或 cards.csv）
- 繁体

不要改 `resources.assets` 里的 TMP 字库，也不要对 `TMP_Text.set_text` 打 Harmony（会损坏资源或白屏）。不要把中文写入 `tutorial_EN`。

## 后续

校对 `overrides.csv` 与机器稿 → 消化漏译表 → rulebook.csv 逐段人工翻译（15 本规则书 What's New / Features 段 + DLC 商店详情）→ 位图标题最后再考虑。

## 变更记录（本进度文档）

| 日期 | 版本 | 更新点 |
| --- | --- | --- |
| 2026-08-20 | v1.2 | 【里程碑】对照表（glossary）升级为唯一事实来源 SSOT；新增 docs/GLOSSARY{,.zh}.md 双语文档作为维护手册；overlay 构建顺序改 glossary → ui.csv reverse-map → 其它层；exact 总数从 925 增加到 1943（+1018 条，修复 Confirm/Start/Close/Yes/No/Done/Undo/Bid/Pass/FAQ/or/XII 等长期漏译按钮）；Promo兽群/Network Connection迷失/Player命名/Would你like等 157 行旧 ui_runtime 机翻垃圾已清除。 |
| 2026-08-20 | v1.2 | 【链路】ingest_untranslated 加 looks_rulebook_body 启发式；规则书段/DLC 段不再走 translate_effect；插件支持 >400 字符和 `<sprite>` 标签的长段 dump（longmax=5000）。 |
| ...    | v1.1 | （见 git log）BepInEx 6 + IL2CPP runtime overlay 上线；Lua `effect_text` 重写；level1 等长替换；TMP 标签剥离后 exact 匹配。 |
