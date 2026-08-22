# L6 — Manual UX checklist (Phase 3 exit)

- 中文：[l6-checklist.zh.md](l6-checklist.zh.md)

Run after deploying plugin **1.5.0+**. Mark each ID after a cold start (fully quit the game, then relaunch).

| ID | Scene / action | Pass criteria | Status |
| --- | --- | --- | --- |
| L6-01 | Cold start → main menu | No English flash of hex/menu labels; no tofu□ flash longer than ~0.5s | ☐ |
| L6-02 | Open DLC / IAP store | Store opens without freeze; long blurbs Chinese; no multi-second hang | ☐ |
| L6-03 | Open any rulebook set | Body paragraphs Chinese within first open (no lingering English page) | ☐ |
| L6-04 | Start offline match | "Play Your Turn" / End Turn show Chinese; no sustained English flicker each turn | ☐ |
| L6-05 | End turn / opponent turn | State marker stays Chinese while game logic still advances | ☐ |
| L6-06 | Return to menu from match | Menu Chinese again; no coverage regression (spot-check 3 labels) | ☐ |

## Notes

- Automated gates: `python -m pytest -q` (includes `test_phase3_antiflicker.py`).
- Native CH locale: **deferred** — game does not ship a `zh-Hans` Unity localization pack; hybrid overlay remains. Revisit if publisher adds official Chinese.
- Do **not** re-enable full-scene TMP sweeps or `SetText(string, float…)` hooks (store freeze).

## Sign-off

| Field | Value |
| --- | --- |
| Plugin version | |
| Tester | |
| Date | |
| Result | ☐ pass / ☐ fail (list failed IDs) |
