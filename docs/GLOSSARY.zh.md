# 中英对照表维护指南（Glossary Maintenance Guide）

> English version: [GLOSSARY.md](GLOSSARY.md)

本项目把「**一个英文 = 一个中文**」的规则集中保存在一张表里，称为 **glossary（对照表）**。它是整个补丁里所有译法的 **唯一事实来源（Single Source of Truth, SSOT）**，无论是手工审校还是程序生成，都要以它为准。

## 1. 文件位置

| 文件 | 作用 |
| --- | --- |
| `glossary/zh-Hans.csv` | **唯一可编辑入口**。直接改这里。 |
| `glossary/zh-Hans.report.txt` | 运行 `glossary_gen.py` 生成的统计报告，只读。 |
| `tools/glossary_gen.py` | 对照表白底维护脚本。里面有 `SEED_ROWS` 常量（程序化补条目用），和 `zh-Hans.csv` 两者会自动去重合并。 |

本指南只讲上面这三个文件的使用；它们最终「喂」给 `tools/overlay.py → overlay.tsv → 插件运行时替换` 这条流水线。

## 2. 表结构（CSV 六列）

`glossary/zh-Hans.csv` 是标准 UTF-8 CSV，**首行必须是表头**：

```csv
en,zh,scope,source,status,notes
```

每列含义：

| 列 | 说明 | 示例 |
| --- | --- | --- |
| **en** | 英文原文（精确匹配用，区分大小写）。如果开头是 `#`，这一行是**分段标题注释**，加载时会被跳过。 | `Confirm` |
| **zh** | 中文定译。留空表示「未译，待后续补」。 | `确认` |
| **scope** | 条目归属的**领域/用途**。见下节「3. scope 清单」。程序用 scope 做两件事：①组合推导（`faction × type = Enlightened Hero → 圣贤英雄`）；②自动生成大小写变体（`label/login/button/shop/ui` 这 5 个 scope 会自动产出 ALLCAPS / alllower / Capitalized 三种 exact key）。 | `button` |
| **source** | 译法来源（见「4. 来源与优先级」）。 | `official-anshashen` |
| **status** | `approved` / `draft`。`approved` 才会进入最终 overlay；`draft` 只作占位，不激活替换。未译留空时建议标 `draft`。 | `approved` |
| **notes** | 备注 / 纠错说明 / 上下文限定。可以写中文或英文。 | `P0 删除对局确认按钮；原 ui_runtime 残留『加入Friend』错误译法`。 |

### 分段标题注释

CSV 中会出现以 `#` 开头的 en，用来做视觉分组（例如「# 系列」、「# 世界」）。这些行**不会被加载到程序里**，只给人看。程序运行时会自动按 scope 重新排序，所以你手动插入的空行或注释位置在下一次 `glossary_gen.py` 运行时会被重排——这是正常的。

## 3. scope 清单

推荐把 scope 当作「条目在哪种 UI 语境下出现」的标签。**同一个英文单词如果在两个语境下译法不同，就写成两行**（用 scope 区分）。例如：

```csv
"Renown","声望","resource","old","draft","2025-08-15 之前把 ASCL 机制误写成声望，必须改为『名望』"
"Renown","名望","resource","new","approved","ASCL（史诗传奇）主要机制；修正后覆盖上面一行"
```

（实际上因为 `_seed_missing` 以 `(en.casefold, scope)` 去重，**同一个 `(en, scope)` 组合只会保留最先写入的一行**。如果要改旧条目的 `zh`，请直接在 CSV 里覆盖，不要添加新行。）

合法 scope 列表：

| scope | 含义 | 是否自动生成大小写变体 | 是否参与组合推导 |
| --- | --- | --- | --- |
| `series`   | 系列/产品定名（Ascension、弑神编年史、创升纪元） | — | — |
| `world`    | 世界/人物名（Vigil、Arha、Samael、Kor） | — | — |
| `faction`  | 四大派系（Enlightened / Void / Mechana / Lifebound）及其扩展 | — | 与 `type` 组合 → `Enlightened Hero` 等 |
| `type`     | 卡类型（Hero / Construct / Monster、Trophy Monster 等） | — | 与 `faction` 组合 |
| `resource` | 资源术语（Rune / Power / Honor / Renown） | — | — |
| `zone`     | 区域（Center Row / Void / Discard / Hand / Deck） | — | — |
| `verb`     | 卡牌操作动词（Draw / Banish / Acquire / Defeat 等） | — | — |
| `label`    | 卡面/面板上的短字段标签（Reward / Fate / Trophy / Reward:） | ✅ | — |
| `button`   | UI 按钮文字（Confirm / Start / Undo / or） | ✅ | — |
| `login`    | Playdek/Asmodee 登录页面（Player Name / Sign Up / Password 等） | ✅ | — |
| `shop`     | DLC 商店 UI（Promo Pack #6 / Purchase Separately 等） | ✅ | — |
| `chapter`  | 规则书章节标题（What's New / Features / RESOURCES 等） | — | — |
| `promo`    | 特典包/Promo 相关（Promo Cards / Promo Pack 1 等不带 # 的变体） | — | — |
| `card`     | 特定卡牌定名（Puggageddon / Defender of Vigil 等） | — | — |
| `credits`  | Credits 页职位/部门标签（Administration / Produced by） | — | — |
| `ui`       | 其它 UI 短语/标题（Create Offline Game / Opponent Bids: 等） | ✅ | — |
| `phrase`   | 规则书常见整段/整句（≥1 句话，通常由 glossary SEED 注入） | — | — |

## 4. 来源与优先级

`source` 列用来追溯译法的出处。冲突时按下面顺序定：**数字越小优先级越高**。

| source | 含义 | 例子 |
| --- | --- | --- |
| 1. `official-anshashen` | 方盒子 365《暗杀神》（弑神编年史–风暴之海区间）的官方中文规则书及维基术语表。CotG–SoS 的基础公共词优先跟它走。 | Rune → 符文；Banish → 放逐 |
| 2. `official-chuangsheng` | 米宝海豚《创升纪元》2017 年起发行的中文官方版本（元素的馈赠、冠军黎明等）。GotE/DC/DL 等新术语跟它走。 | Renown → 名望；Dreambind → 梦缚 |
| 3. `community` | 360 百科「暗杀神」词条、方塔桌游评测、BGA/Steam 评测、民间合集里已经**广泛固化**的译法。 | Promo Pack → 特典包 |
| 4. `new` | 没有任何公开中文官方来源的全新词，按已锁定术语推导出的补译。注意随时可能被更权威的来源推翻。 | Deliverance Rulebook → 救赎规则书 |
| 5. `old` | 历史遗留旧译，用来和新译对比的占位。一般标 `status=draft` 不让它激活，只作为注释说明历史错在哪。 | （对照用）Renown → 声望（旧） |

**硬规则**：
- 游戏内系列名只写 **《创升纪元》**，不用「《暗杀神》」或「Ascension」的纯音译。
- 四大派系 / 符文 / 战力 / 荣誉 / 放逐：**一旦敲定全系列不改口**，即使早期官方和新官方不同，也按上面优先级 1 的 `official-anshashen` 处理（历史用户最熟悉的译法）。

## 5. 两种维护方式

### 方式 A：手工改 CSV（90% 的日常情况）

适用场景：
- 新发现一个按钮漏译（例如 `FAQ` 想改成「常见问题」）
- 某个术语用户提了更好的译法（例如把之前写成 `SBT → 石刃赛事` 改回 `SBT → SBT`，保留缩写）
- 规则书里一个专有名词想统一（例如新增 `For millennia, the world of Vigil ...` 整段）

操作步骤：

```powershell
# 1. 用任何 CSV 编辑器直接打开 glossary/zh-Hans.csv
code glossary/zh-Hans.csv
# 或 Excel / LibreOffice / VS Code "Edit csv" 插件

# 2. 找到/新增一行，填好 6 列（尤其是 scope 别错）
# 例：    Confirm,确认,button,community,approved,P0 删除对局按钮

# 3. 重新生成报告（可选但推荐；会重排 scope 顺序并校验）
python tools/glossary_gen.py
#   输出类似：
#   read existing rows: 458 (comments: 18)
#   seed rows injected (absent before): 0
#   rewrote zh-Hans.csv: 458 data rows
#   derived: exact=426  allow_short(len<=4)=49
#   report → zh-Hans.report.txt

# 4. 构建翻译层
python tools/build_zh.py
#   会写出 overlay.tsv + cards.csv + cards_packed.csv + ui.full.csv

# 5. 部署到游戏（请先关闭游戏！）
python tools/patch.py enable --locale zh-Hans
```

### 方式 B：程序补条目（批量加入 / 复用 SEED_ROWS）

适用场景：
- 要一次性加 10 多条新的「label」或「login」短语
- 想把一组新的译法固化成「以后每次都保留」的基线
- 不希望每次手动改 CSV 时都手工填 6 列

操作：

1. 打开 `tools/glossary_gen.py`，滚动到最下面的 `SEED_ROWS = [` 列表。
2. 按同样的 dict 格式追加新条目。每一条都必须填 6 个 key：
   ```python
   {"en": "Puggageddon", "zh": "巴哥末日", "scope": "card",
    "source": "official-anshashen", "status": "approved",
    "notes": "官方 lua_cards 定名；入 glossary 防 overlay 漏匹配"},
   ```
3. 跑 `python tools/glossary_gen.py`。脚本会把 `SEED_ROWS` 和现有 `zh-Hans.csv` 按 `(en.casefold, scope)` 自动去重合并——已经存在的条目不会被覆盖（保留你手改的版本），不存在的条目会被追加进去。
4. 后续「构建 → 部署」和方式 A 一样：`build_zh.py` → `patch.py enable`。

**注意**：如果 `SEED_ROWS` 和你手改的 CSV 同一个 `(en, scope)` 行冲突，**CSV 里的手改版本赢**。因此方式 A 和 B 可以混用，不会互相覆盖。这是「glossary 双入口」的设计意图：

```
SEED_ROWS (程序化基线)  ──merge_seed──▶  ┌─────────────┐
                                          │  zh-Hans.csv │  ← 人类审校/覆盖
人类手工编辑                          ──▶  └─────────────┘
                                                          │
                                              derive_glossary_exact()
                                                          │
                                                          ▼
                                             overlay.py → overlay.tsv
```

## 6. 未译英文反馈闭环（Untranslated Loop）

当你已经部署了补丁，但是游戏里还有英文怎么办？BepInEx 插件会在运行时把**所有它没替换成功的英文**写到下面这个文件里：

```
<AscensionGame>/AscensionGame_Data/StreamingAssets/zh-cn/untranslated.tsv
```

格式：三列，`kind\tsrc\tcontext`。

| kind | 含义 | 程序处理路径 |
| --- | --- | --- |
| `K` | 没见过的 `LocalizationService` key（给出 sample 英文以便你去 `loc/en/sheets/*.csv` 对照） | 仅打印在控制台，需要手动到 `loc/zh-Hans/ui.csv` 或 `cards.csv` 补译 |
| `E` | 短英文 UI 文本（≤400 字符） | 默认进入 `translate_effect` 流水线，但「看起来像规则书段」的（由 `looks_rulebook_body()` 判断）会被截走，改走下面 L 路径 |
| `L` | 长规则书段 / DLC 商店文案（>400 字符或含 `<sprite>` 标签） | 写入 `rulebook.csv`，zh 留空等待人译 |

**消化方法**：

```powershell
# 1. 玩完一遍游戏，把所有漏译界面都踩一遍（规则书 15 本逐本点开，商店 DLC 逐页点）
# 2. 关游戏
# 3. 运行 ingest，它会把 untranslated.tsv 拆分到两个表
python tools/ingest_untranslated.py

# 运行完一般看到类似输出：
#   no new exact UI strings to ingest
#   appended 37 long strings -> rulebook.csv (total 52, 12 already translated)
#   already covered or skipped: 194
#   missing loc keys: 2
#     Key_FAQ_Header  Frequently Asked Questions
#     Key_Promo_11    Promo Pack #11
```

然后：

- **短 UI 文本**（进了 `ui_runtime.csv` 的）：打开看一下，如果机翻能接受就留着；如果不行就改 `zh`，或者直接把 `(en, 正确译法)` 作为新行加入 glossary（推荐后者，因为 glossary 是 SSOT）。
- **长段/DLC/规则书**（进了 `rulebook.csv` 的）：**不要用 translate_effect**。它们的 `zh` 列 ingest 时故意留空——请手工打开 `loc/zh-Hans/rulebook.csv` 逐行做完整自然语言翻译。翻译时记得保留原文的 rich-text 标签（`<b>`、`<br>`、`<smallcaps>`、`<sprite=N>`、`<color=#...>` 等），原样搬到对应 zh 里。
- **缺失的 key（Missing Loc Keys）**：到 `loc/en/sheets/Common_Strings.csv` / `Ascension_Cards.csv` 里查 sample 对应的 key，在 `loc/zh-Hans/ui.csv` / `cards.csv` 补一行。

完成一轮后再跑 `build_zh.py → patch.py enable → 进游戏 → 又产生一批 untranslated.tsv → ingest`，循环几次就能把漏网英文压到极少。

## 7. 构建链路速查

```
glossary/zh-Hans.csv  ←── glossary_gen.py (SEED_ROWS)
      │
      ▼
tools/overlay.py  ── derive_glossary_exact() ──► exact map
      │                                  ├──► allow_short set
      │                                  └──► faction×type combinators
      │
      ├─ ui.csv (Key_* 反向推 exact)
      ├─ cards.csv / combat_log.csv / tutorial.csv
      ├─ ui_runtime.csv (短 UI 段)
      ├─ rulebook.csv (长规则书/DLC 段)
      └─ extras dict (legacy 兜底)
      │
      ▼
loc/zh-Hans/overlay.tsv     (K + E rows)
      │
      ▼
StreamingAssets/zh-cn/overlay.tsv   BepInEx 插件运行时读这个
         │
         ▼
   LocalizationService.GetTextByKey(key)  →  K 行替换
   TMP_Text.set_text(value)               →  E 行精确替换
                        (NormalizeUi 去富文本后再匹配一次)
```

快速命令备忘：

```powershell
# 只重建 glossary 报告 + 合并 SEED_ROWS
python tools/glossary_gen.py

# 从 glossary 到 overlay 的全量构建（不部署）
python tools/build_zh.py

# 构建 + 部署（关游戏再运行）
python tools/patch.py enable --locale zh-Hans

# 只重新部署 plugin DLL + overlay
python -c "import sys; sys.path.insert(0,'tools'); from bepinex import enable_runtime; enable_runtime()"

# 消化新的漏译表（游戏退出后）
python tools/ingest_untranslated.py
```

## 8. 常见陷阱

| 陷阱 | 为什么不好 | 正确做法 |
| --- | --- | --- |
| 直接改 `ui_runtime.csv` 而不改 glossary | `ui_runtime.csv` 只是 ingest 的产物，下一轮 ingest 时若同一段再次出现会被 glossary 覆盖。而且多人协作时 glossary 才是共享的真相。 | 凡是「以后还会再用到的术语」一律入 glossary；`ui_runtime.csv` 只留临时一次性短语。 |
| 把「玩家姓名」写成 `Player Name,玩家姓名,ui` 而不是 `...,login` | 大小写变体只对 `{label,login,button,shop,ui}` 这 5 个 scope 生效，但 login 的含义更准——其实两个都行，但 scope 越精准越好维护。 | 按真实语境挑最细的 scope；不细也没关系，大不了下次看到再调。 |
| 在 `notes` 里写了大量解释但 `status` 还是 `draft` | `draft` 行不会激活翻译！如果是修正旧译请把 status 改成 `approved`。 | 审校流程最后一步一定检查 `status == approved`。 |
| glossary 里有 `Reward:` 但规则书里显示的是 `REWARD:`，你又加了一行 `REWARD:` → 被去重 | merge_seed 用 `.casefold()` 做 (en, scope) 键，所以 `Reward:` 和 `REWARD:` 视为相同。大小写变体由 `derive_glossary_exact()` 自动生成。 | 不用手动加大写版本。如果你在 exact 调试里发现仍没命中，先检查 scope 是否在那 5 个里。 |
| 把 `RESOURCE`、`FACTIONS` 这种 ALLCAPS 规则书大标题写成 scope=`label` | 规则书标题按规定是 `chapter` scope，不会自动生成大小写变体——正好，避免误匹配。 | 保持用 `chapter`，并手动补一行 `RESOURCES`（allcaps）和一行 `Resources:`（title-case 带冒号）以防两种 UI 都出现。 |
| 用 `translate_effect` 或 `name_lexicon.py` 直接对规则书正文批量替换 | 词汇替换破坏自然中文句式，会产生「符文为一的两main resources在Ascension」这种中英混杂垃圾。 | 规则书正文必须整句人工翻译。 |

## 9. 变更记录

| 日期 | 版本/里程碑 | 更新点 | 触发原因 |
| --- | --- | --- | --- |
| 2026-08-20 | v0.1 | 文档首次创建；glossary 从 ad-hoc CSV 升级为 SSOT（458 行 / 426 推导 exact） | 规则书中英混杂、Confirm/Start 等短按钮漏译长期存在，需要统一维护入口 |
| 2026-08-20 | v0.1 | overlay.py 重写：put_exact 默认不覆盖以保护 glossary 优先级；label/login/button/shop/ui 自动生成大小写变体；faction×type 组合推导 | 解决 glossary 条目被 ui.csv reverse-map 反向覆盖、以及 `REWARD:` vs `Reward:` 不同 casing 的漏匹配 |
| 2026-08-20 | v0.1 | ingest_untranslated.py 新增 `looks_rulebook_body()` 启发式 | 避免 translate_effect 被误用于规则书叙事/DLC 文案导致中英混杂 |
| 2026-08-20 | v0.1 | `ui_runtime.csv` 清理 L130+ 共 157 行机翻残片 | 历史 ingest 遗留，如 `Promo兽群 #6` / `Network Connection迷失` 等错误译法 |
