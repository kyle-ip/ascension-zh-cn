# Feasibility and releasability: Chinese language patch for Ascension (Steam)

- Default language of this docs set: **English**. Chinese: [feasibility-report.zh.md](feasibility-report.zh.md)
- Target: Steam install of Playdek’s *Ascension: Deckbuilding Game*
- Engine: Unity 6000.0.58f2, IL2CPP
- Date: 2026-08-18
- Verdict: **technically feasible**. Ship as an **external, togglable** patch. Do **not** treat in-place edits of the install tree as the only delivery. Prefer existing official and established community Chinese copy; translate only the gaps in the same register.

Chinese titles used in the wild: **《创升纪元》** (*Chuangsheng Jiyuan*) and **《暗杀神》** (*Ansha Shen*). Both should be acknowledged.

---

## 1. Naming and releasability

The Steam digital client lists English only. Two Chinese names both matter:

| Name | Role | Use in the patch |
| --- | --- | --- |
| **暗杀神** | 2011 Box365 import name; Wikipedia title; early physical sets and player memory | Primary historical source for terms, card names, flavor |
| **创升纪元** | Series name after Surfin’ Meeple’s 2017 license; later physical expansions | Public patch name; expansion titles; newer set copy |

Public label: **Chinese language patch for *创升纪元* (also known as *暗杀神*)**. In-game, do not force a single title; settings can say Simplified / Traditional Chinese and mention both names in the blurb.

**Releasability / copyright:**

- Fan language pack for personal use, not official DLC. Do not bundle or redistribute the full game.
- OK to distribute: self-authored or compiled **CSV, glossary, font license notes, toggle tool**.
- Not OK: scanned official rulebook art, official card images, cracked clients.
- Physical Chinese card text belongs to the original publishers. Using it in a private patch is a different risk than publishing a public dump. If the patch is published, prefer verifiable public glossary terms (wiki, published reviews) plus original translation, with source tags.

---

## 2. Technical feasibility (summary)

The build already has a localization pipeline, which is more favorable than most IL2CPP games.

| Layer | Location | Form | Localization difficulty |
| --- | --- | --- | --- |
| Card name / effect / flavor | `cards_EN` in `resources.assets` | CSV, TMP rich text over art | Low (no card redraw) |
| Tutorial | `tutorial_EN` etc. | CSV | Low |
| Menus / dialogs | Google Sheet cache: `EN FR PT DE ES PL NL IT RU JP CH` | `CH` column reserved but empty | Medium |
| Lua display fields | `StreamingAssets/Lua/*_cards.lua` | `display_name` / `effect_text` | Low, but **`card_name` is an ID — never translate** |
| Combat log | Lua `string.format("%s gains %d runes")` | Few format strings | Low |
| UI fonts | TextMeshPro Latin SDF | No CJK | **High — do first** |
| Rulebooks | `rulebooks/rulebook*` | Mostly full images | Optional later |

Card faces are not English baked into textures. `CARDNAME_*` / `EFFECT_*` overlay the art (e.g. drop cap `<size=104>V</size>oid Initiate`). Chinese needs its own typography (do not copy English drop caps).

The sheet already has empty **CH / JP** columns and `Key_SelectLanguage`. The external patch must still own the on/off switch: selecting empty CH without a font yields tofu; without a string table it falls back to English.

---

## 3. Copy policy: reuse first, translate the rest

### 3.1 Priority (mandatory)

1. **Official physical Chinese** (Box365 *暗杀神*, Surfin’ Meeple *创升纪元*): names, effects, keywords.
2. **Established community usage** (wiki terms; long-standing card names such as 天选者 and flavor 你我皆梦他为梦者).
3. If the two official lines conflict: CotG–SoS follow *暗杀神*; post-2017 sets (GotE and later) follow *创升纪元*. Shared keywords (rune / power / honor / banish) stay **one** series-wide glossary.
4. Sets with no source: new translation from the locked glossary. Effect lines stay short and imperative; flavor may be literary, but do not invent a second set of resource names.

### 3.2 Locked shared terms (wiki / early official register)

| English | Chinese | Notes |
| --- | --- | --- |
| Rune | 符文 | Not 符石 / 魔力 |
| Power | 战力 | Not 力量 (collides with Magic: The Gathering) |
| Honor | 荣誉 | |
| Hero / Construct / Monster | 英雄 / 神器 / 怪物 | Early official Construct = 神器 |
| Acquire / Defeat / Banish / Discard | 获取 / 击败 / 放逐 / 弃牌 | |
| Center Row / Void | 中央牌列 / 虚空区 | |
| Apprentice / Militia / Mystic / Heavy Infantry / Cultist | 学徒 / 民兵 / 秘教士 / 重装步兵 / 邪教徒 | |
| Enlightened / Lifebound / Mechana / Void | Lock after checking physical cards | Faction names may differ by publisher era; tag sources |

### 3.3 Sets in this install vs Chinese sources (estimate)

About **938** Lua card tables; `cards_EN` has about **2330** display strings (852 names + 839 effects + 515 flavor + labels).

| Code | File | ~Cards | English set | Chinese source |
| --- | --- | --- | --- | --- |
| CotG | set1 | 48 | Chronicle of the Godslayer | **Official *暗杀神：弑神编年史*** — reuse the whole set |
| CotG10 | set1_anniv | 48 | 10th anniversary | Same lineage as CotG; reuse, then patch anniversary diffs |
| RotF | set2 | 31 | Return of the Fallen | **Official *邪神归来*** |
| SoS | set3 | 53 | Storm of Souls | **Official *灵魂风暴*** |
| IH | set4 | 58 | Immortal Heroes | Official *不朽英雄* (confirm physical completeness) |
| RoV | set5 | 53 | Rise of Vigil | *祈夜崛起*; early import evidence |
| DU | set6 | 44 | Darkness Unleashed | Common compilation name 黑暗释放; verify physical |
| RU | set7 | 65 | Realms Unraveled | Compilation usage 领域解开 |
| DoC | set8 | 56 | Dawn of Champions | 冠军黎明 |
| DS | set9 | 73 | Dreamscape | 梦境 |
| WoS | set10 | 43 | War of Shadows | 暗影之战 |
| GotE | set11 | 60 | Gift of the Elements | **Official *创升纪元：元素的馈赠*** |
| VotA | set12 | 51 | Valley of the Ancients | Check whether Surfin’ Meeple printed Chinese |
| Del | set13 | 49 | Delirium | Late set — **likely new translation** |
| Dlvr | set14 | 58 | Deliverance | Late set — **likely new translation** |
| LGND | set17 | 73 | Legends | Retail clues for 史诗传奇; verify |
| promo | promo etc. | ~52 | Promos | Reuse where a physical promo exists |

**Reuse estimate:**

- High confidence official: CotG + RotF + SoS + GotE ≈ **190+** cards (~20–25%). Work is **transcription / proof**, not invention.
- Medium (compilations, reviews, established fan names): IH–WoS, ~**40–50%**. Check source per card; not a finished dump.
- Low, glossary-based new translation: Delirium / Deliverance / some Legends / unmatched promos, ~**25–35%**.

There is no complete public official Chinese card dump to import. Most effort is **collecting physical/photos/review citations into a keyed table**, not inventing names from scratch.

Scripts: Simplified Chinese is the master lexicon. Traditional via OpenCC, then human pass on TW/HK wording (获取/獲得, 卡组/牌组). Settings switch **zh-Hans / zh-Hant**; not two independent creative translations.

---

## 4. External and togglable (required)

The patch **must not** only permanently overwrite `resources.assets` / Lua. Players must be able to turn Chinese off without reinstalling or Steam verify.

Layout:

```text
[patch root, outside the Steam install tree]
  patch.json          enabled: true/false
                      locale: zh-Hans | zh-Hant
  glossary/           terms and source tags
  loc/cards.zh-Hans.csv
  loc/ui.zh-Hans.csv
  loc/tutorial.zh-Hans.csv
  fonts/              CJK TMP or dynamic font (license required)
  loader/             runtime inject (preferred) or apply/restore
```

| Action | Behavior |
| --- | --- |
| On | At launch, load external strings + CJK font over the display layer |
| Off | No inject; client matches vanilla English |
| Hans / Hant | Swap lexicons (and font subset) only; no gameplay data changes |

**Implementation order:**

1. Runtime hook `LocalizationService.GetTextByKey` / `UILocalizedText` (BepInEx-IL2CPP or equivalent). CSV stays in the patch folder.
2. If Unity 6 IL2CPP inject is unstable: overlay `StreamingAssets` and replaceable TextAssets **with backups**; the toggler Apply / Restore. Still external (lexicon not in the game Git tree), but off requires one restore pass.
3. Do not prioritize patching hardcoded strings in `GameAssembly.dll`.

Install lives under Program Files: writes need admin; Steam verify undoes overlays. That is why external + restore is mandatory.

Multiplayer: display-name-only is usually fine. If the server compares display strings, play one match with the patch on. Keep internal `card_name` in English.

---

## 5. Effort

Estimate for **one person** who knows Unity mods and can check physical cards/photos. Includes Hans/Hant proof. Excludes rulebook redraws.

| Phase | Work | Person-days | Depends on |
| --- | --- | --- | --- |
| A. Prove | Export CSV; confirm overlay vs Lua; one-card Chinese smoke | 1–2 | AssetRipper / hex trial |
| B. Font | CJK fallback (common Hans+Hant) into TMP | 2–4 | Font license (Source Han / Noto CJK) |
| C. Toggle | External folder + on/off/locale; runtime inject first | 4–8 | Unity 6 + IL2CPP toolchain |
| D. Glossary | Tag official / community / new | 2–3 | Physical cards, reviews, wiki |
| E. Card copy | ~2330 strings: transcribe → verify fan → fill gaps | 10–18 | D; late sets are mostly new |
| F. UI + tutorial | ~300 UI keys + ~104 tutorial lines | 2–4 | No official menu Chinese; follow glossary |
| G. Traditional | Convert + keyword pass | 2–3 | E/F Simplified frozen |
| H. QA | Solo, gallery, tutorial, toggle round-trip, optional online | 3–5 | C done |

**Totals:**

| Scope | Person-days | Calendar (~15 h/week) |
| --- | --- | --- |
| MVP: font + toggle + core three sets (CotG/RotF/SoS) + main menu | **18–28** | ~4–6 weeks |
| Full: all sets Hans+Hant + tutorial + stable external toggle | **26–47** | ~2–3 months |
| Rulebook image localization | +5–15 | Optional, not MVP |

Buffer: Unity 6 asset rewrite or IL2CPP inject failure may add **~1 week** to C (fallback to backup overlay).

**Out of scope (blows the schedule):** redrawing cards, full rulebook art, changing `card_name`, voice, supporting the 2019 “Chinese portable” client (different build).

---

## 6. Suggested releases

1. **MVP (playable):** external toggle + CJK font + main UI + core-set cards (reuse *暗杀神*).
2. **V1:** all official / high-confidence sets reused; remaining sets newly translated Simplified.
3. **V1.1:** Traditional switch; tutorial.
4. **V2 (optional):** rulebooks, leftover hardcoded lines.

---

## 7. Next (not started)

1. Keep the patch project **outside** the Steam tree (`docs/` is analysis only; no lexicons here).
2. Export `cards_EN` and the UI table into an empty “English key → source status” sheet.
3. Smoke one Chinese card name plus a temporary CJK font.
4. In parallel, test whether BepInEx / Il2CppInterop loads on this Unity 6 build.

---

## Docs convention

- Filenames: English (`kebab-case.md`).
- Pair: default English file + `*.zh.md` Chinese sibling.
- English is canonical when the two drift.
