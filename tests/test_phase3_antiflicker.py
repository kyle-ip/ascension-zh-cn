# -*- coding: utf-8 -*-
"""L3/L4: Phase 3 anti-flicker invariants (plugin source gates)."""
from __future__ import annotations

import re
from pathlib import Path

from conftest import ROOT

PLUGIN = ROOT / "plugin" / "AscensionZhCn" / "Plugin.cs"

# Snapshot of board state markers that require display/logic split.
# Changing this list without an L6 checklist update is a regression.
EXPECTED_STATE_MARKERS = {
    "Play Your Turn",
    "PLAY YOUR TURN",
    "End Turn",
    "END TURN",
}


def _plugin_src() -> str:
    assert PLUGIN.is_file(), f"missing {PLUGIN}"
    return PLUGIN.read_text(encoding="utf-8")


def test_plugin_version_is_phase3():
    src = _plugin_src()
    assert 'BepInPlugin("ascension.zh.cn", "Ascension Chinese overlay", "1.5.1")' in src


def test_prerender_hook_present():
    src = _plugin_src()
    assert "PatchPreRender" in src
    assert "Camera.onPreRender" in src
    assert "ForceStateMarkersToChinese" in src


def test_l1_exact_fallback_in_loc_postfix():
    src = _plugin_src()
    assert "LookupExactOrNormalized(__result)" in src
    assert "viaExact" in src
    assert "LocPostfix" in src


def test_rulebook_panel_relocalize_on_scene_and_tick():
    src = _plugin_src()
    assert "RelocalizeKnownPanels" in src
    assert "KnownPanelNames" in src
    assert '"Rulebook"' in src
    assert src.count("RelocalizeKnownPanels()") >= 2


def test_state_marker_snapshot_stable():
    src = _plugin_src()
    for marker in EXPECTED_STATE_MARKERS:
        assert f'"{marker}"' in src, f"missing state marker {marker!r}"


def test_no_store_panel_sweep():
    """Store roots must stay out of KnownPanelNames string literals (IAP freeze)."""
    src = _plugin_src()
    m = re.search(
        r"static readonly string\[\] KnownPanelNames\s*=\s*\{(.*?)\};",
        src,
        re.S,
    )
    assert m, "KnownPanelNames array missing"
    literals = {s.lower() for s in re.findall(r'"([^"]+)"', m.group(1))}
    for banned in ("store", "iap", "shop", "dlcstore", "inappstore"):
        assert not any(banned in lit for lit in literals), (
            f"KnownPanelNames must not include {banned}: {sorted(literals)}"
        )
