# Progress

Steam *Ascension: Deckbuilding Game*, Unity 6000.0.58f2 (IL2CPP). In-game series name: 《创升纪元》; first set remains 弑神编年史 (Chronicle of the Godslayer).

Install: [README](../README.md). Design: [architecture.md](architecture.md). **Roadmap / phase exits:** [roadmap.md](roadmap.md). Glossary guide: [GLOSSARY.md](GLOSSARY.md). Chinese notes: [progress.zh.md](progress.zh.md).

## Principles

1. Regression tests: `python -m pytest -q`; CI mirrors the same gates.
2. Inventory-driven coverage: `loc/inventory/strings.csv` + `gates.json`; statuses `missing|draft|reviewed|waived`.

## Phase status

| Phase | Status | Notes |
| --- | --- | --- |
| **T** Test + inventory foundation | **Done** | Inventory + pytest L0–L4 + CI ceilings |
| **0** Baseline + runtime hotfixes | **Done** | Rulebook/DLC filled; UI junk cleaned; store stable + long-copy Chinese (plugin **1.4.5**) |
| **1** Coverage loop `missing→0` | **Done** | `missing_total=0`; empty flavors waived; acronym names reviewed |
| **2** Per-pack `draft→reviewed` | **Done** | All packs reviewed; `draft_total=0`; 启迪=0; credits waived |
| **3** Anti-flicker UX | **Coded (L6 pending)** | Plugin **1.5.0**: onPreRender markers, L1 Exact fallback, rulebook panel refresh; see docs/l6-checklist.md |

Inventory snapshot: **3616** rows; **0** missing; **0** draft; reviewed 2712; waived 904. Gates at **phase 3** (coverage/draft ceilings still 0; antiflicker gates in `test_phase3_antiflicker`).

## Done

BepInEx 6 overlays `GetTextByKey` + TMP/UI `set_text` Exact/Norm + YaHei CJK fallback. Lua display fields rewritten (not internal card IDs). Partial equal-length `level1` patches.

Overlay ≈ 3084 keys / 2299 exact. Rulebook/DLC long copy in `rulebook.csv` with runtime Exact+Norm+partial. Regression via `tests/` + `gates.json`.

## Phase 2 closed

- All pack effects/names → `reviewed` (938+938)
- Flavors with source → translated `reviewed`; empty source → `waived(no_flavor_in_source)`
- UI / tutorial / combat_log / shop_dlc → `reviewed`
- Rulebook credits (Latin person names kept) → `waived(credits_names)`
- Glossary: Enlightened→圣贤; ban-term 「启迪」 hits = 0
- `lua_cards.csv`: no `machine` source; center deck → 中央牌库
- Gates: `phase=2`, `max_draft_total=0` + per-domain draft ceilings

## Phase 3 shipped (code)

- Sync CJK fallback before `_ready` / L2 (kept)
- `Camera.onPreRender` + LateUpdate dual force for state markers
- `LocPostfix` Exact/Norm fallback when Keys miss (effective L1 expansion)
- Scene load + tick: `RelocalizeKnownPanels` (rulebook roots only; no store)
- Faster marker scan on match-like scenes; native CH deferred (no official zh-Hans pack)
- L6 checklist: `docs/l6-checklist.md` (Exit requires manual cold-start sign-off)

## Later

- L6 manual sign-off; bitmap titles (waived); Traditional Chinese

## Changelog (this file)

| Date | Version | Delta |
| --- | --- | --- |
| 2026-08-22 | v1.5.1 | Coverage holes: scrub mixed card flavors; achievements in ui_runtime; gallery Exact maps; faster rulebook Relocalize |
| 2026-08-22 | Phase 3 / 1.5.0 | Anti-flicker coded: onPreRender markers; L1 Exact fallback; rulebook panels; L6 checklist; gates phase 3 |
| 2026-08-22 | Phase 2 | Quality closed: `draft_total=0`; all packs reviewed; 启迪=0; credits waived; gates phase 2 + draft ceilings; pytest 25 |
| 2026-08-22 | Phase 1 | Coverage closed: `missing_total=0`; flavor waive policy; acronym names; Loading rulebook fix |
| 2026-08-22 | Phase 2 kickoff | Terminology: 启迪→圣贤 everywhere; glossary gate ceiling 0 |
| 2026-08-22 | v1.4.5 | Store/rulebook long-copy restored; full overlay deploy checks; Phase T/0 complete |
| 2026-08-22 | v1.4.3–1.4.4 | Store freeze mitigation then coverage restore |
| 2026-08-22 | v1.3 | Architecture docs; Inventory + pytest; rulebook/DLC baseline |
| … | v1.1–1.2 | Runtime overlay + glossary SSOT |
