# 《创升纪元》简体中文补丁：进度与计划

- 日期：2026-08-19
- 游戏：Steam《Ascension: Deckbuilding Game》（Playdek）
- 引擎：Unity 6000.0.58f2，IL2CPP
- 公开中文名：**只使用《创升纪元》**。扩展名「弑神编年史」保留（对应 Chronicle of the Godslayer），不要改成创升纪元。

这不是官方 DLC。仓库只分发自写工具、术语表和译文，不分发客户端、卡图或规则书扫描件。

---

## 玩家怎么用

1. 完全退出游戏。
2. 运行仓库里 `scripts/publish-installer.ps1` 生成的 `dist\AscensionZhCn-Setup.exe`（与旁边的 `payload` 文件夹放在一起；exe 约 160MB，含 .NET 运行时，**不进 Git**）。
3. 确认游戏目录后点 **安装汉化** 或 **恢复英文**。

游戏装在 `Program Files` 下时，若写入失败，请右键「以管理员身份运行」。Steam「验证游戏文件完整性」会拆掉补丁；用安装器恢复即可，不必验证。

---

## 当前进度（可用）

运行时以 **BepInEx 6 IL2CPP 插件**为主，Harmony 只补丁 `LocalizationService.GetTextByKey`。不要对 `TMP_Text.set_text` 打补丁（会白屏退出），也不要改 `resources.assets` 里的 TMP 字库（会损坏资源）。

| 层 | 做法 | 状态 |
| --- | --- | --- |
| 菜单 / 卡面 loc 键 | `overlay.tsv` 的 `K` 行 + Harmony | 可用。`Ascension_Cards` 约 2600+ 键（含 Legends） |
| 硬编码 UI | `E` 精确替换 + 每 30 帧扫描 TMP | 主菜单、回合、派系侧栏、通讯弹窗、内购 Owned/价格 等已覆盖 |
| 图鉴 Lua 效果 | 改写 `effect_text` / `flavor_text`（**不改** `card_name` / `display_name`） | `..` 拼接已整段替换 |
| 场景按钮 | `level1` 等长 UTF-8 替换 | Offline / Online / 商店 / 通讯 / Cancel |
| 中文字体 | 延迟挂 YaHei TMP fallback | Windows 可用 |
| 开关 | 安装器或 `python tools/patch.py enable\|disable` | 可还原英文 |

插件版本：**1.3.0**。漏译采集默认开启，写入：

`AscensionGame_Data/StreamingAssets/zh-cn/untranslated.tsv`

维护者可再跑：

```powershell
python tools/ingest_untranslated.py
python tools/build_zh.py
python tools/patch.py enable --locale zh-Hans
```

锁定术语：符文 / 战力 / 荣誉；获取 / 击败 / 放逐；学徒 / 民兵 / 秘教士 / 重装步兵 / 邪教徒；Construct = 神器；派系 启迪 / 生命 / 机械 / 虚空。

---

## 已知限制（不要靠截图逐条猜）

这些不是 loc 键，当前安装器也改不了：

1. **位图标题**：主 Logo 下的 DECKBUILDING GAME、离线列表大标题 Offline Games、内购页 Downloadable Content、扩展缩写图标（CotG、LGS 等）。
2. **规则书正文**：`resources.assets` 里打包的英文长文，中文放不进等长替换。
3. **教程 TextAsset**：不要把中文写进 `tutorial_EN`（UTF-8 会乱码）。教程走 overlay 的 `TUTORIAL_*` 键。
4. **风味 / 效果**：机器草稿仍有夹杂英文；图鉴效果靠 Lua，过长的 `EFFECT_*` 无法写入 packed JSON（Harmony 仍能显示 overlay 译文）。
5. **繁体**：未做。

---

## 下一步（建议顺序）

1. **漏译闭环**：用 1.3.0 玩一遍通讯、内购、图鉴 Legends、设置；把 `untranslated.tsv` ingest 进 `ui_runtime.csv`，再发布安装器。
2. **校对**：`overrides.csv` 锁死的弑神编年史卡名优先；其余扩展机器稿按术语表人工过一遍。
3. **Lua / 效果**：继续清夹杂英文；ingest 漏掉的 `K` 键补进 `cards.csv` / `ui.csv`。
4. **规则书**：单独做运行时 overlay（不能等长塞进 TextAsset）。
5. **位图标题**：最后考虑；需要贴图或自定义绘制，工作量大、易坏。
6. **安装体验**：GitHub Release 挂上 `AscensionZhCn-Setup.exe`（本地 `dist/` 不进 Git）；可选首次安装时自动等 BepInEx 生成 interop。

不要做：改 TMP atlas、把 TTF 拼进 `LiberationSans`、Harmony 钩 `TMP_Text.set_text`。

---

## 仓库分工

| 进 GitHub | 不进 GitHub（`.gitignore` + 下载脚本） |
| --- | --- |
| 译文 `loc/`、术语表、插件源码、安装器源码 | `state/dotnet-sdk/`、BepInEx zip、字体二进制、`state/backups/`（游戏文件）、`dist/` 发布目录 |
| `scripts/download-tools.ps1` | 下载后的 SDK / BepInEx 包 |

维护者机器：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download-tools.ps1
powershell -ExecutionPolicy Bypass -File scripts/publish-installer.ps1
```

GitHub Actions 在 `main` 和 `v*` 标签上构建同一安装器。玩家可从 Actions 产物或 Release 下载 `AscensionZhCn-Setup.exe`（需与 `payload` 放在一起）。

译文管线仍用 Python（`extract_en.py` / `build_zh.py` / `patch.py`）。玩家不需要 Python。
