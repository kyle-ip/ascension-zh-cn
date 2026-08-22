# -*- coding: utf-8 -*-
"""Shared path helpers for tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH = ROOT / "loc" / "zh-Hans"
EN = ROOT / "loc" / "en"
GLOSSARY = ROOT / "glossary" / "zh-Hans.csv"
INVENTORY = ROOT / "loc" / "inventory"
OVERLAY = ZH / "overlay.tsv"
