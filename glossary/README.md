# Glossary

Canonical Chinese terms for review and bulk replace. **This file is a short index only; the full maintenance workflow lives at [docs/GLOSSARY.zh.md](../docs/GLOSSARY.zh.md) / [docs/GLOSSARY.md](../docs/GLOSSARY.md). Read that before editing.**

| File | Use |
| --- | --- |
| [zh-Hans.csv](zh-Hans.csv) | **审校入口**：`en,zh,scope,source,status,notes`。改这里后跑 `python tools/glossary_gen.py`，再 `python tools/build_zh.py`，然后 `python tools/patch.py enable --locale zh-Hans`（部署前请先关闭游戏）。 |
| [zh-Hans.report.txt](zh-Hans.report.txt) | 运行 glossary_gen.py 产生的报告（行数 / exact 数 / draft 数），只读。 |
| [terms.csv](terms.csv) | 历史术语表（含繁体列）；由 `zh-Hans.csv` 同步，新改动只写简体表。 |

## 来源优先级（source 列）

1. `official-anshashen`：方盒子 365《暗杀神》及维基「游戏术语」（CotG–SoS 公共规则词）。
2. `official-chuangsheng`：米宝海豚《创升纪元：元素的馈赠》等 2017 年后官方。
3. `community`：360 百科、方塔桌游、合集/评测已固化译法。
4. `new`：无公开官方来源，按已锁定术语补译。

冲突时：早期基础包跟《暗杀神》；GotE 及以后跟《创升纪元》；符文/战力/荣誉/放逐全系列不改口。游戏内系列名只用「创升纪元」，不用「暗杀神」。

## scope 速查

`series` / `world` / `faction` / `type` / `resource` / `zone` / `verb` / `label` / `button` / `login` / `shop` / `chapter` / `promo` / `card` / `credits` / `ui` / `phrase`。详见维护指南。

图鉴侧栏派系名带 TMP 首字放大（如 `<size=141%>M</size>onster`）；插件会剥掉标签后再按本表替换。本表只收可复用术语，不含全卡名（卡名在 `loc/zh-Hans/overrides.csv`）。
