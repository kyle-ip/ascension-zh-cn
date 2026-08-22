# Docs

| | |
| --- | --- |
| [architecture.zh.md](architecture.zh.md) | **系统设计（中文）** — 整体架构、技术选型、离线/运行时原理、词库流、约束与测试原则（含 Mermaid 架构图） |
| [architecture.md](architecture.md) | **System design (English)** — architecture, tech choices, offline/runtime principles, lexicon pipeline, QA (with Mermaid diagrams) |
| [blog-why-chinese.zh.md](blog-why-chinese.zh.md) | **科普博文（中文）** — 为什么《Ascension》能汉化：浅显原理、图示、路线图与展望 |
| [roadmap.zh.md](roadmap.zh.md) | **执行计划 / 分阶段 Exit（中文）** — 硬原则、Inventory、测试分层、T→3 路线图 |
| [roadmap.md](roadmap.md) | **Roadmap / phase exits (English)** — principles, inventory, test layers, phases T→3 |
| [progress.zh.md](progress.zh.md) | 进度与后续工作（中文） |
| [progress.md](progress.md) | Progress (English) |
| [GLOSSARY.zh.md](GLOSSARY.zh.md) | **中英对照表维护指南（中文）** — 表结构 / scope 说明 / 两种维护方式 / 未译闭环 / 构建链路 / 陷阱 |
| [GLOSSARY.md](GLOSSARY.md) | **Glossary Maintenance Guide (English)** — schema, scopes, two editing workflows, untranslated loop, build pipeline, pitfalls |
| [feasibility-report.zh.md](feasibility-report.zh.md) | 可行性与可发行性（中文） |
| [feasibility-report.md](feasibility-report.md) | Feasibility / shipping notes (English) |
| [glossary/zh-Hans.csv](../glossary/zh-Hans.csv) | 中英术语对照 CSV（审校 / 替换入口） |
| [../loc/inventory/](../loc/inventory/) | 覆盖库存矩阵与 `gates.json` 回归天花板 |
| [../tests/](../tests/) | pytest 回归（L0–L4） |

Install steps are in the [README](../README.zh.md). New contributors: read **architecture** then the Glossary Maintenance Guide. Before changing translations or the plugin, run `python -m pytest -q`.
