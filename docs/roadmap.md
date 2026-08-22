# Ascension Chinese Patch — Roadmap

- 中文：[roadmap.zh.md](roadmap.zh.md)
- See also: [architecture.md](architecture.md) · [progress.md](progress.md)

This is the **execution-plan SSOT**: principles, phased exits, and how Inventory / pytest gates bind to releases.

## Hard principles

1. **Regression tests first** — assert before changing lexicon/plugin/build; `python -m pytest -q` locally and in CI.
2. **Inventory-driven, no silent omissions** — every displayable domain is registered; status ∈ `{missing|draft|reviewed|waived}`; ship domains require `missing=0`; `waived` needs a reason.

## Phases

| Phase | Focus | Exit |
| --- | --- | --- |
| **T** | Inventory + pytest L0–L4 + CI ceilings | Green tests; all domains registered |
| **0** | Rulebook/DLC baseline + UI junk cleanup + store/rulebook runtime hotfixes | Long copy Chinese; store does not freeze |
| **1** | Coverage loop: `missing → 0` by domain | **Done (2026-08-22):** missing=0; empty flavors waived; acronym names reviewed |
| **2** | Quality: `draft → reviewed` per expansion pack | **Done (2026-08-22):** `draft_total=0`; 启迪=0; credits waived; gates phase 2 |
| **3** | UX anti-flicker / architecture convergence | **Coded (2026-08-22):** plugin 1.5.0; L6 checklist pending manual sign-off |

## Runtime stability notes

Do not Harmony-patch TMP `SetText(string, float, …)` overloads (IAP freeze). Prefer Exact + NormalizedExact for long copy; replace tags with spaces in normalize; keep overlay deploy size checks so truncated payloads cannot regress (`exact≈988`).

## Changelog

| Date | Notes |
| --- | --- |
| 2026-08-22 | Phase 2 quality closed (`draft_total=0`; glossary 启迪=0; gates phase 2); Phase 3 next |
| 2026-08-22 | Phase 1 coverage closed (`missing_total=0`); Phase 2 next |
| 2026-08-22 | Initial roadmap checked into docs from the defect-analysis plan; Phase T/0 done, Phase 1 next |
