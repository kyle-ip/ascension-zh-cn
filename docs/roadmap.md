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
| **1** | Coverage loop: `missing → 0` by domain | Gate ceilings lowered; no silent skips |
| **2** | Quality: `draft → reviewed` per expansion pack | Glossary gates; per-pack reviewed effects |
| **3** | UX anti-flicker / architecture convergence | L6 checklist; no coverage regressions |

## Runtime stability notes

Do not Harmony-patch TMP `SetText(string, float, …)` overloads (IAP freeze). Prefer Exact + NormalizedExact for long copy; replace tags with spaces in normalize; keep overlay deploy size checks so truncated payloads cannot regress (`exact≈988`).

## Changelog

| Date | Notes |
| --- | --- |
| 2026-08-22 | Initial roadmap checked into docs from the defect-analysis plan; Phase T/0 done, Phase 1 next |
