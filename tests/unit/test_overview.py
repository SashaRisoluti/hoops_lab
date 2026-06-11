"""Unit tests for the Overview design system and analytics helpers."""

from __future__ import annotations

import pandas as pd

from dashboard.components.theme import (
    BLUE,
    CONFERENCES,
    ORANGE,
    RED,
    TEAM_ACCENTS,
    pctl_color,
)
from hoops_lab.analytics.overview import (
    conference_standing,
    overview_flags,
    zone_bucket,
)


def test_pctl_color_tricolor_buckets() -> None:
    # Design rule: orange = good (>=66th), blue = mid (33-66), red = weak (<33rd).
    assert pctl_color(82) == ORANGE
    assert pctl_color(66) == ORANGE
    assert pctl_color(50) == BLUE
    assert pctl_color(33) == BLUE
    assert pctl_color(20) == RED


def test_team_maps_cover_all_30_franchises() -> None:
    assert len(CONFERENCES["WEST"]) == 15
    assert len(CONFERENCES["EAST"]) == 15
    all_tricodes = set(CONFERENCES["WEST"]) | set(CONFERENCES["EAST"])
    assert len(all_tricodes) == 30
    assert set(TEAM_ACCENTS) == all_tricodes
    assert TEAM_ACCENTS["DAL"] == "#0064B1"  # accent used by the design
    assert TEAM_ACCENTS["LAL"] == "#FDB927"


def test_zone_bucket_groups_shot_zones() -> None:
    assert zone_bucket("Restricted Area") == "RIM"
    assert zone_bucket("In The Paint (Non-RA)") == "MID"
    assert zone_bucket("Mid-Range") == "MID"
    assert zone_bucket("Left Corner 3") == "CORNER 3"
    assert zone_bucket("Right Corner 3") == "CORNER 3"
    assert zone_bucket("Above the Break 3") == "ABOVE BREAK 3"
    assert zone_bucket("Backcourt") is None


def _game_rows(n: int, efg: float, tov: float, pm: float) -> list[dict]:
    return [{"OFF_EFG": efg, "OFF_TOV_PCT": tov, "PLUS_MINUS": pm} for _ in range(n)]


def test_overview_flags_detect_cold_shooting_and_turnovers() -> None:
    # Season: 20 solid games; last 5: cold shooting and turnover spike.
    games = pd.DataFrame(
        _game_rows(20, efg=0.56, tov=11.0, pm=6.0) + _game_rows(5, efg=0.50, tov=15.0, pm=-4.0)
    )
    flags = overview_flags(games)

    rules = {f["rule"] for f in flags}
    assert {"cold_shooting", "turnover_trend", "form_dip"} <= rules
    severities = {f["rule"]: f["severity"] for f in flags}
    assert severities["cold_shooting"] == "HIGH"


def test_overview_flags_quiet_on_steady_form() -> None:
    games = pd.DataFrame(_game_rows(25, efg=0.55, tov=12.0, pm=4.0))
    flags = overview_flags(games)

    assert len(flags) == 1
    assert flags[0]["severity"] == "LOW"


def test_conference_standing_ranks_by_wins() -> None:
    ratings = pd.DataFrame({"TEAM_ID": [1, 2, 3], "W": [50, 60, 41]})
    teams = pd.DataFrame({"team_id": [1, 2, 3], "abbreviation": ["DAL", "OKC", "BOS"]})
    rank, conference = conference_standing(ratings, teams, team_id=1)

    assert conference == "WEST"  # DAL is a Western Conference team
    assert rank == 2  # OKC (60 W) ahead, BOS is East and does not count
