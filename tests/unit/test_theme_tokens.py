"""Unit tests for the Worldcup26 design tokens (spec 2026-07-24)."""

from __future__ import annotations

import json

from dashboard.components.theme import (
    COLOR_GOOD,
    COLOR_MID,
    COLOR_PRIMARY,
    COLOR_WEAK,
    COLOR_WEAK_SOFT,
    TOKENS,
    pctl_color,
    pctl_text_color,
    plotly_layout,
    tokens_json,
)


def test_worldcup26_palette_values() -> None:
    assert COLOR_GOOD == "#16c47f"
    assert COLOR_MID == "#ffd100"
    assert COLOR_WEAK == "#e0262c"
    assert COLOR_PRIMARY == "#0052ff"


def test_pctl_color_boundaries() -> None:
    # Spec rule: >=66 good, 33-66 mid, <33 weak — thresholds unchanged.
    assert pctl_color(100) == COLOR_GOOD
    assert pctl_color(66) == COLOR_GOOD
    assert pctl_color(65.9) == COLOR_MID
    assert pctl_color(33) == COLOR_MID
    assert pctl_color(32.9) == COLOR_WEAK
    assert pctl_color(0) == COLOR_WEAK


def test_pctl_text_color_readable_variants() -> None:
    assert pctl_text_color(80) == COLOR_GOOD
    assert pctl_text_color(50) == COLOR_MID
    assert pctl_text_color(10) == COLOR_WEAK_SOFT


def test_pctl_text_color_boundaries() -> None:
    assert pctl_text_color(66) == COLOR_GOOD
    assert pctl_text_color(65.9) == COLOR_MID
    assert pctl_text_color(33) == COLOR_MID
    assert pctl_text_color(32.9) == COLOR_WEAK_SOFT


def test_tokens_json_roundtrip() -> None:
    payload = json.loads(tokens_json())
    assert payload == TOKENS
    assert payload["primary"] == "#0052ff"
    assert payload["good"] == "#16c47f"


def test_plotly_layout_uses_inter_on_transparent_paper() -> None:
    layout = plotly_layout()
    assert "Inter" in layout["font"]["family"]
    assert layout["paper_bgcolor"] == "rgba(0,0,0,0)"


def test_plotly_layout_returns_isolated_copies() -> None:
    first = plotly_layout()
    first["font"]["family"] = "Comic Sans"
    first["margin"]["l"] = 999
    second = plotly_layout()
    assert second["font"]["family"].startswith("Inter")
    assert second["margin"]["l"] == 10
