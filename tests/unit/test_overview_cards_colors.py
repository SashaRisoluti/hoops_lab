"""Color-semantics tests for the Overview builders after the restyle."""

from __future__ import annotations

from dashboard.components.overview_cards import (
    flag_box,
    radar_figure,
    team_band,
    tricolor_legend,
)
from dashboard.components.theme import COLOR_GOOD, COLOR_MID, COLOR_PRIMARY, COLOR_WEAK


def test_flag_box_low_is_informational_blue() -> None:
    # LOW flags are informational -> primary blue, NOT the mid-percentile yellow.
    assert COLOR_PRIMARY in flag_box("LOW", "steady form")


def test_flag_box_high_is_weak_red() -> None:
    assert COLOR_WEAK in flag_box("HIGH", "cold shooting")


def test_legend_shows_semantic_triple() -> None:
    html = tricolor_legend()
    assert COLOR_GOOD in html
    assert COLOR_MID in html
    assert COLOR_WEAK in html


def test_radar_fill_derives_from_primary() -> None:
    fig = radar_figure({"eFG%": 60.0, "TOV": 40.0, "ORB": 50.0})
    assert fig.data[0].fillcolor == "rgba(0,82,255,0.32)"


def test_team_band_has_no_hardcoded_hex_badge_background() -> None:
    html = team_band(
        accent="#0052ff",
        name="Dallas",
        subtitle="sub",
        last5=["W", "L"],
        last_game="vs BOS · W +5",
        abbr="DAL",
    )
    assert "#161B23" not in html
