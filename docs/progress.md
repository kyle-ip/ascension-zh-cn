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
| **1** Coverage loop `missing→0` | **Done (coverage)** | `missing_total=0`; empty flavors waived; acronym names reviewed |
| **2** Per-pack `draft→reviewed` | **Next** | Pack order in roadmap; lower 「启迪」 hits |
| **3** Anti-flicker UX | Not started | Plugin changes need tests |

Inventory snapshot: **3616** rows; **0** missing; draft 2471; reviewed 244; waived 901. Gates at **phase 1** (`max_missing_total: 0`).

## Done

BepInEx 6 overlays `GetTextByKey` + TMP/UI `set_text` Exact/Norm + YaHei CJK fallback. Lua display fields rewritten (not internal card IDs). Partial equal-length `level1` patches.

Overlay ≈ 3084 keys / 2299 exact. Rulebook/DLC long copy in `rulebook.csv` with runtime Exact+Norm+partial. Regression via `tests/` + `gates.json`.

## Phase 2 gaps

- Large `draft` debt across effects/UI/flavor
- Glossary ban 「启迪」 still has a hit ceiling (drive to 0)
- Machine-mixed English leftovers inside card effects

## Changelog (this file)

| Date | Version | Delta |
| --- | --- | --- |
| 2026-08-22 | Phase 1 | Coverage closed: `missing_total=0`; flavor waive policy; acronym names; Loading rulebook fix |
| 2026-08-22 | v1.4.5 | Store/rulebook long-copy restored; full overlay deploy checks; Phase T/0 complete |
| 2026-08-22 | v1.4.3–1.4.4 | Store freeze mitigation then coverage restore |
| 2026-08-22 | v1.3 | Architecture docs; Inventory + pytest; rulebook/DLC baseline |
| … | v1.1–1.2 | Runtime overlay + glossary SSOT |
