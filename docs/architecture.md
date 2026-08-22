# Ascension Chinese Patch — System Design

- 中文：[architecture.zh.md](architecture.zh.md)
- Scope: Steam *Ascension: Deckbuilding Game* (Playdek), repo `ascension-zh-cn`
- Engine: Unity **6000.0.58f2**, **IL2CPP**
- Purpose: architecture, technology choices, runtime/offline principles, data flow, constraints, and quality gates (with Mermaid diagrams)

See also: [progress.md](progress.md) · [GLOSSARY.md](GLOSSARY.md) · [feasibility-report.md](feasibility-report.md)

When this file and the Chinese copy disagree, prefer the Chinese copy for product terminology; prefer this file for neutral technical wording if they drift—keep them in sync on edits.

---

## 1. Goals and non-goals

### 1.1 Goals

| Goal | Notes |
| --- | --- |
| Playable Simplified Chinese | Menus, card names/effects, tutorial, rulebook text blocks, DLC store copy |
| External, toggleable | Installer can apply or restore English without a permanent one-way hijack |
| Consistent terminology | `glossary/zh-Hans.csv` is SSOT; prefer official/community Ascension Chinese |
| Maintainable + regression-safe | Inventory-driven coverage; pytest + CI |
| Legal fan pack | Ship tables, tools, font notes, toggler—not the game, card art, or scanned rulebooks |

### 1.2 Non-goals

- Redrawing bitmap titles / rulebook scan pages
- Changing Lua `card_name` (internal IDs)
- Full Traditional Chinese productization (OpenCC + manual keywords later)
- Relying solely on the empty stock **CH** language column (future convergence option)

---

## 2. Where game text lives

| Source | Location | Shape | Hook |
| --- | --- | --- | --- |
| Card face strings | `resources.assets` → `cards_EN` | CSV TextAsset + TMP | Offline blob + `GetTextByKey` |
| UI / common | Loc JSON / sheets (`CH` empty upstream) | Keys | Offline + overlay Keys |
| Tutorial | `tutorial_EN` | CSV | External CSV; do not break CLICK/link hit-tests |
| Codex / effects | `StreamingAssets/Lua/*_cards.lua` | `effect_text` / `flavor_text` | Offline rewrite; never touch `card_name` |
| Hardcoded UI | Prefabs / direct TMP assigns | English literals | Runtime Exact |
| Rulebooks | Rulebook* TMP + bitmaps | Text vs art | Exact / long dump; bitmaps waived |
| Menu chips | `level1` | Length-prefixed UTF-8 | Same-byte-length replace |

Card faces use overlay text (often English drop-caps via `<size=…>`), not baked English in art.

### 2.1 Text sources and hooks

```mermaid
flowchart LR
  subgraph Game["In-game text sources"]
    Cards["cards_EN<br/>CSV TextAsset"]
    Loc["loc JSON / Sheet<br/>EN…JP CH"]
    Tut["tutorial_EN"]
    Lua["Lua *_cards.lua<br/>display/effect/flavor"]
    Hard["Prefab / hardcoded"]
    RB["Rulebook TMP + bitmaps"]
    L1["level1 menu chips"]
  end

  subgraph Patch["Patch hooks"]
    Off["Offline<br/>same-slot / equal-len / fields"]
    RT["Runtime<br/>Key / Exact"]
    Waive["waived<br/>bitmap titles"]
  end

  Cards --> Off
  Cards --> RT
  Loc --> Off
  Loc --> RT
  Tut --> Off
  Tut --> RT
  Lua --> Off
  Hard --> RT
  RB --> RT
  RB --> Waive
  L1 --> Off
```

---

## 3. Architecture overview

Hybrid: **restorable offline file patches** + **BepInEx runtime overlay**.

```mermaid
flowchart TB
  subgraph Src["ascension-zh-cn (source)"]
    G["glossary/"]
    L["loc/"]
    T["tools/"]
    P["plugin/"]
    I["installer/"]
    F["fonts/"]
    Te["tests/"]
  end

  Src -->|build_zh / overlay.py| Overlay["overlay.tsv + tables"]
  Src -->|publish| Setup["AscensionZhCn-Setup.exe"]

  Overlay --> Deploy
  Setup -->|install / enable| Deploy

  subgraph Deploy["Steam Game Root"]
    LuaFiles["StreamingAssets/Lua/*.lua<br/>offline: effect/flavor"]
    Assets["resources.assets<br/>offline: cards_EN / loc JSON"]
    Scene["AscensionGame_Data/level1<br/>offline: menu"]
    ZhDir["StreamingAssets/zh-cn/overlay.tsv<br/>runtime: dictionary"]
    Plugin["BepInEx/plugins/AscensionZhCn.dll<br/>runtime: plugin"]
  end
```

ASCII (plain-text environments):

```text
ascension-zh-cn  --build-->  overlay.tsv + tables
                 --install--> Steam tree:
                   Lua / resources.assets / level1   (offline)
                   StreamingAssets/zh-cn/overlay.tsv (runtime data)
                   BepInEx/plugins/AscensionZhCn.dll (runtime)
```

| Layer | When | Components | Role |
| --- | --- | --- | --- |
| Offline | Installer | Lua / Asset / Scene patchers | Durable display fields with backups |
| Lexicon build | Dev | glossary → overlay.py | `overlay.tsv` (`K` + `E` rows) |
| Runtime | Every launch | BepInEx 6 IL2CPP plugin | Loc hooks, Exact rewrite, CJK TMP fallback |

```mermaid
flowchart LR
  subgraph Dev["Dev machine"]
    Gl["glossary SSOT"] --> Build["build_zh / overlay.py"]
    Build --> TSV["overlay.tsv<br/>K + E"]
  end

  subgraph Install["Install time"]
    TSV --> PS["PatchService"]
    PS --> LuaP["LuaPatcher"]
    PS --> AssetP["AssetPatcher"]
    PS --> SceneP["ScenePatcher"]
    PS --> DeployP["Deploy DLL + zh-cn/"]
  end

  subgraph Runtime["Every launch"]
    DeployP --> Plug["AscensionZhCn"]
    Plug --> L1h["L1 GetTextByKey"]
    Plug --> L2h["L2 set_text"]
    Plug --> Font["CJK TMP fallback"]
  end
```

Disable = restore backups + remove plugin / `zh-cn` (keep `state/backups`).

```mermaid
flowchart LR
  Enable["enable / install"] --> Backup["write state/backups"]
  Backup --> PatchFiles["patch Lua / assets / level1"]
  PatchFiles --> DropPlugin["drop DLL + overlay"]
  Disable["disable / restore EN"] --> Restore["restore from backups"]
  Restore --> Remove["remove plugin + zh-cn/"]
  Remove -.->|keep backups| Backup
```

---

## 4. Technology choices

| Concern | Choice | Why |
| --- | --- | --- |
| Injection | BepInEx 6 Unity IL2CPP | Works on this Unity 6 build |
| UI rewrite | Harmony postfix `GetTextByKey` + prefix TMP/UI `set_text` | Keys + hardcoded English |
| Fonts | Runtime TMP fallback (YaHei / SimHei / optional TTF) | Baking fonts into assets crashed historically |
| Terms | Glossary CSV SSOT | Reviewable; derives case / faction×type |
| Delivery | WinForms setup + payload | One-click; admin when under Program Files |
| Long rulebook/DLC | Exact + paragraph indexes | TMP often renders one paragraph at a time |
| QA | pytest + inventory matrix | No silent coverage loss |

Rejected: irreversible tree hijack; full-scene TMP sweep every frame on rulebook (freezes); word-salad MT into main tables.

```mermaid
flowchart LR
  subgraph Chosen["Chosen"]
    BIE["BepInEx 6 IL2CPP"]
    Harm["Harmony L1 postfix + L2 prefix"]
    Font["runtime TMP fallback"]
    Gloss["glossary CSV SSOT"]
    Setup["WinForms installer"]
    QA["pytest + Inventory"]
  end

  subgraph Rejected["Rejected"]
    Irr["irreversible overwrite"]
    Sweep["per-frame rulebook Sweep"]
    Bake["fonts baked into assets"]
    MT["dirty MT into main tables"]
  end
```

---

## 5. Runtime plugin

Plugin id `ascension.zh.cn` (`plugin/AscensionZhCn/Plugin.cs`).

**Boot:** bind dump config → load overlay → patch L1 immediately → try sync CJK → if ready, arm L2 setters + `sceneLoaded` → inject `CjkFontBehaviour` (retries, periodic relocalize, per-frame state markers).

```mermaid
sequenceDiagram
  participant P as AscensionZhCn
  participant O as overlay.tsv
  participant L as LocalizationService
  participant T as TMP / UI.Text
  participant F as CJK Fallback

  P->>P: bind Dump* config
  P->>O: LoadOverlay()
  O-->>P: Keys + Exact + indexes
  P->>L: PatchLocalization() L1 immediately
  P->>F: EnsureCjkFallback()
  alt font ready
    P->>P: _ready = true
    P->>T: PatchTextSetters() L2
    P->>P: sceneLoaded + CjkFontBehaviour
  else font not ready
    P->>P: L1 only; Behaviour retries font
  end
```

**L1:** postfix `GetTextByKey` → `Keys`. Prefer keys for card faces; avoid duplicate Exact for those strings.

```mermaid
flowchart LR
  Call["GetTextByKey(key)"] --> Post["Harmony postfix"]
  Post --> Hit{"Keys hit?"}
  Hit -->|yes| Zh["__result = zh"]
  Zh --> Embed{"has ${…}?"}
  Embed -->|yes| Expand["expand nested keys"]
  Embed -->|no| Out["return zh"]
  Expand --> Out
  Hit -->|no| Dump["optional dump kind=K"]
  Dump --> En["return original"]
```

**L2:** prefix `set_text` / `SetText` → Exact / normalized / prefix / sentence / contains. Skip tutorial CLICK/link. Re-entrancy guard `_inRewrite`. No word-level MT on rulebook-like text.

```mermaid
flowchart TD
  Set["set_text / SetText(value)"] --> Guard{"_inRewrite?"}
  Guard -->|yes| Pass["pass through"]
  Guard -->|no| Tut{"CLICK / link?"}
  Tut -->|yes| Pass
  Tut -->|no| E1["Exact"]
  E1 -->|miss| E2["strip-tags normalize"]
  E2 -->|miss| E3["prefix index"]
  E3 -->|miss| E4["sentence index"]
  E4 -->|miss| E5["contains"]
  E5 -->|miss| DumpE["optional dump kind=E"]
  E1 -->|hit| Rew["rewrite value → zh"]
  E2 -->|hit| Rew
  E3 -->|hit| Rew
  E4 -->|hit| Rew
  E5 -->|hit| Rew
  Rew --> Mesh["write TMP mesh"]
  DumpE --> Mesh
  Pass --> Mesh
```

**State markers:** show Chinese, cache English for `get_text`, LateUpdate force—may cost one English frame, avoids logic oscillation.

```mermaid
sequenceDiagram
  participant Game as Game logic
  participant TMP as TMP
  participant Plug as Plugin

  Game->>TMP: set_text("Play Your Turn")
  Plug->>TMP: show Chinese; cache English
  Game->>TMP: get_text()
  Plug-->>Game: cached English (logic compare)
  Note over TMP: possible one English frame
  Plug->>TMP: LateUpdate force Chinese
```

**Fonts:** create TMP fallback from OS or packaged TTF; attach to TMP settings and live fonts. Chinese from L1 without fallback = tofu flash.

```mermaid
flowchart TD
  Start["EnsureCjkFallback"] --> OS["CreateFontAsset<br/>YaHei / SimHei"]
  OS -->|fail| TTF["read game dir or zh-cn/*.ttf"]
  OS -->|ok| Attach
  TTF -->|ok| Attach["attach TMP_Settings + font fallbacks"]
  TTF -->|fail| Retry["Behaviour periodic retry"]
  Attach --> Ready["_ready → allow L2"]
  Retry --> OS
```

**Dump:** `untranslated.tsv` kinds `K`/`E`/`L`; ingest carefully (filter noise).

```mermaid
flowchart LR
  Miss["runtime miss"] --> Dump["untranslated.tsv<br/>K / E / L"]
  Dump --> Ingest["ingest_untranslated.py"]
  Ingest --> Filter["manual noise filter"]
  Filter --> Gloss["glossary / ui / rulebook"]
  Gloss --> Rebuild["overlay.py rebuild"]
```

---

## 6. Offline installer

`PatchService`: Lua fields → assets (`cards_EN`, padded loc JSON; skip overlong / hint / tutorial keys) → same-length `level1` → deploy BepInEx + overlay. Steam verify integrity undoes offline layer.

```mermaid
flowchart TD
  Start["PatchService.InstallAsync"] --> Lua["1. LuaPatcher<br/>effect / flavor (backup)"]
  Lua --> Assets["2. AssetPatcher<br/>restore backups then apply"]
  Assets --> Cards["cards_EN same-size blob"]
  Assets --> Loc["loc JSON pad; skip if overlong"]
  Cards --> Scenes
  Loc --> Scenes["3. ScenePatcher<br/>level1 equal-length"]
  Scenes --> Bep["4. deploy BepInEx + overlay.tsv"]
  Bep --> Done["playable Chinese"]

  Steam["Steam verify integrity"] -.->|undoes offline| Re["re-install patch"]
```

---

## 7. Lexicon pipeline

1. Edit `glossary/zh-Hans.csv` (approved only ships)
2. `glossary_gen.py` / `build_zh.py` / `overlay.py` → `overlay.tsv`
3. Rulebook human dict: `translate_rulebook.py` → `rulebook.csv`
4. Enable copies overlay next to the game

Row types: `K\tkey\tzh`, `E\ten\tzh` (empty zh = placeholder; not for release).

```mermaid
flowchart TD
  G["glossary approved<br/>exact + faction×type"] --> O
  C["cards.csv → Keys"] --> O
  U["ui.csv / tutorial.csv → Keys"] --> O
  R["EN table reverse Key_* → Exact"] --> O
  X["combat_log / ui_runtime / rulebook → Exact"] --> O
  P["rulebook paragraph split"] --> O
  E["extras / Player N / Round N"] --> O
  O["overlay.py"] --> TSV["overlay.tsv"]
  TSV --> Krows["K rows key→zh · L1"]
  TSV --> Erows["E rows en→zh · L2"]
```

```mermaid
flowchart LR
  subgraph Tools["tools/"]
    BZ["build_zh.py"]
    OV["overlay.py"]
    TR["translate_rulebook.py"]
    IG["ingest_untranslated.py"]
    PT["patch.py"]
  end

  BZ --> Tables["cards / lua_cards / ui / …"]
  Tables --> OV
  TR --> RB["rulebook.csv"]
  RB --> OV
  IG --> Cand["candidates"]
  Cand --> Tables
  OV --> Out["loc/zh-Hans/overlay.tsv"]
  Out --> PT
  PT -->|enable| Game["game root zh-cn/"]
```

---

## 8. Repo layout

`glossary/`, `loc/{en,zh-Hans,inventory}/`, `plugin/`, `installer/`, `tools/`, `tests/`, `fonts/`, `docs/`, `state/backups/`, `patch.json`.

```mermaid
flowchart TB
  Root["ascension-zh-cn"]
  Root --> glossary["glossary/ SSOT"]
  Root --> loc["loc/"]
  loc --> en["en/ EN extract"]
  loc --> zh["zh-Hans/ tables + overlay"]
  loc --> inv["inventory/ coverage matrix"]
  Root --> plugin["plugin/ BepInEx"]
  Root --> installer["installer/"]
  Root --> tools["tools/"]
  Root --> tests["tests/"]
  Root --> fonts["fonts/"]
  Root --> docs["docs/"]
  Root --> state["state/backups/"]
```

In-game: `StreamingAssets/zh-cn/`, `BepInEx/plugins/`, `BepInEx/config/ascension.zh.cn.cfg`.

```mermaid
flowchart LR
  subgraph SA["StreamingAssets/zh-cn/"]
    O1["overlay.tsv"]
    Log["plugin.log"]
    U["untranslated.tsv"]
  end
  subgraph BX["BepInEx/"]
    DLL["plugins/AscensionZhCn.dll"]
    O2["plugins/overlay.tsv copy"]
    Cfg["config/ascension.zh.cn.cfg"]
  end
  O1 --> DLL
  O2 --> DLL
  Cfg --> DLL
```

---

## 9. Structural limitations

Flicker (post-hoc rewrite), empty rulebook shells until applied, MT pollution, multi-path inconsistency, equal-length skips, waived bitmaps. Remediation is inventory + tests + phased coverage/quality/UX work.

```mermaid
flowchart LR
  Flicker["EN→ZH flicker"] --> Fix1["earlier font/L2 · expand L1"]
  Empty["empty rulebook shell"] --> Fix2["Inventory + ingest"]
  MT["MT pollution"] --> Fix3["ban from main tables + glossary gates"]
  Multi["multi-path inconsistency"] --> Fix4["cross-diff tests"]
  Len["equal-length miss"] --> Fix5["Exact / native CH"]
  BMP["bitmap English"] --> Fix6["waived · dedicated redraw"]
```

---

## 10. Quality: tests and inventory

Layers L0–L6 (build invariants → coverage → glossary gates → pure functions → golden snapshots → install smoke → manual UX). Inventory statuses: `missing | draft | reviewed | waived`. Ship with `missing=0` in scope; waived listed with reasons.

```mermaid
flowchart TB
  L0["L0 build invariants / TSV"] --> L1["L1 Inventory coverage"]
  L1 --> L2["L2 glossary gates"]
  L2 --> L3["L3 pure normalize"]
  L3 --> L4["L4 golden snapshots"]
  L4 --> L5["L5 install smoke"]
  L5 --> L6["L6 manual UX"]
```

Phases: **T** harness → **0** baseline fill → **1** coverage → **2** per-set review → **3** anti-flicker.

```mermaid
stateDiagram-v2
  [*] --> missing
  missing --> draft: fill translation
  draft --> reviewed: per-set review
  reviewed --> [*]
  missing --> waived: bitmap / hit-test / protocol ID
  waived --> [*]: reason required

  note right of missing
    ship scope: missing = 0
  end note
```

```mermaid
flowchart LR
  T["T test harness"] --> P0["0 baseline fill"]
  P0 --> P1["1 coverage loop"]
  P1 --> P2["2 per-set review"]
  P2 --> P3["3 anti-flicker"]
```

---

## 11. Compatibility

Display-only; keep `card_name`; admin may be required under Program Files; first BepInEx interop launch may need a second enable.

```mermaid
flowchart TB
  Display["display-only"] --> Safe["no win/lose / logic-table edits"]
  ID["keep card_name English"] --> Net["stable online IDs"]
  Admin["Program Files → admin"] --> Install["installer elevation prompt"]
  First["first BepInEx interop"] --> Second["may need second enable"]
```

---

## 12. Changelog

| Date | Notes |
| --- | --- |
| 2026-08-22 | Add Mermaid diagrams (sources, overview, layers, enable/disable, runtime L1/L2/markers/fonts, offline install, lexicon, layout, defects, tests/Inventory) |
| 2026-08-22 | Initial system design (EN companion to architecture.zh.md) |
