# 译文工作台（Workbench）

这里是**给人填的配置表**。仓库对外只保留三个入口：

```powershell
cd <this-repo>
.\install.ps1   # 新机器一次：依赖（不改游戏）
.\enable.ps1    # 改完 loc\workbench\*.csv 的 zh 后：加载并启用汉化
.\disable.ps1   # 恢复纯英文原版
```

游戏目录：在 `config.json` 填 `gameRoot`，或留空让脚本询问一次（会写回配置）。

`enable.ps1` 会自动：加载工作台 → 成就表 → 重建 overlay → 编译/部署插件 → 启用 BepInEx。

## 首次或需要重新抽英文底稿时

维护者可用内部工具重抽底稿（非日常入口）：

```powershell
python tools/workbench_extract.py
# 再编辑 zh，然后 .\enable.ps1
```

## 分区文件

| 文件 | 游戏里对应什么 | 你怎么填 |
| --- | --- | --- |
| `rulebook.csv` | 15 扩展游戏内规则书 TMP | 填 `zh` |
| `ui_keys.csv` | 官方 loc 键（`Key_*`） | 填 `zh` |
| `ui_exact.csv` | 硬编码英文 Exact | 填 `zh` |
| `cards_lua.csv` | 图鉴 Lua 名/效果/风味 | 填 `zh` |
| `cards_sheet.csv` | `CARDNAME_*` 等 | 填 `zh` |
| `tutorial.csv` | 教程 | 填 `zh` |
| `glossary.csv` | 术语 | 填 `zh` |
| `runtime_gaps.csv` | 运行时漏译 | 有把握再填 |
| `achievements.csv` | 成就名/说明（由 `build_achievements.py` 维护） | 一般不用手改 |
| `_index.csv` | 统计 | 只读 |

## 列说明

| 列 | 含义 |
| --- | --- |
| `id` | 稳定编号；**勿改** |
| `en` | 英文原文；**勿改** |
| `zh` | **只改这一列** |
| `status` | `empty` / `draft` / `done` / `skip` |

Excel 请另存为 **CSV UTF-8**。保留 TMP 标签（`<sprite>`、`<color>` 等）。

改完后务必先退出游戏，再跑 `.\enable.ps1`。
