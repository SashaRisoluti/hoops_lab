"""Unit tests for the spatial shot-profile feature engineering.

All fixtures are hand-built and deterministic; expected values are computed
by hand. Coordinates follow the ShotChartDetail convention: LOC_X/LOC_Y in
tenths of feet, origin at the hoop.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from hoops_lab.features.shot_spatial_features import (
    COURT_BOUNDS,
    ZONE_FEATURES,
    build_player_season_shot_profile,
    build_spatial_bins,
    build_team_season_shot_profile,
    build_team_window_profile,
)


def _shot(
    player: int,
    zone: str,
    made: int,
    x: int = 0,
    y: int = 0,
    team: int = 1,
    season: str = "2025-26",
    shot_type: str = "2PT Field Goal",
    distance: int = 5,
) -> dict:
    return {
        "PLAYER_ID": player,
        "PLAYER_NAME": f"Player {player}",
        "TEAM_ID": team,
        "TEAM_NAME": f"Team {team}",
        "season": season,
        "SHOT_ZONE_BASIC": zone,
        "SHOT_MADE_FLAG": made,
        "SHOT_TYPE": shot_type,
        "SHOT_DISTANCE": distance,
        "LOC_X": x,
        "LOC_Y": y,
    }


def _sample_shots() -> pd.DataFrame:
    """Player 1: 4 shots — 2 rim (1 made), 1 midrange (made), 1 corner 3 (made).

    Player 2: 1 shot only (filtered out by min_attempts >= 2).
    """
    rows = [
        _shot(1, "Restricted Area", 1, x=0, y=10, distance=1),
        _shot(1, "Restricted Area", 0, x=5, y=15, distance=2),
        _shot(1, "Mid-Range", 1, x=100, y=120, distance=16),
        _shot(1, "Right Corner 3", 1, x=230, y=20, shot_type="3PT Field Goal", distance=23),
        _shot(2, "Above the Break 3", 0, x=0, y=270, shot_type="3PT Field Goal", distance=27),
    ]
    return pd.DataFrame(rows)


# ---- build_spatial_bins ------------------------------------------------------


def test_spatial_bins_assigns_expected_cells() -> None:
    shots = _sample_shots()
    binned = build_spatial_bins(shots, bins=(12, 10))

    assert {"bin_x", "bin_y", "bin_id"}.issubset(binned.columns)
    assert binned["bin_x"].between(0, 11).all()
    assert binned["bin_y"].between(0, 9).all()
    # x = 0 sits exactly mid-range of [-250, 250] -> bin 6 of 12.
    assert binned.loc[0, "bin_x"] == 6
    # y = 10 in [-52.5, 417.5] -> (10 + 52.5) / 470 * 10 = 1.32 -> bin 1.
    assert binned.loc[0, "bin_y"] == 1


def test_spatial_bins_clips_out_of_bounds_coordinates() -> None:
    shots = pd.DataFrame([_shot(1, "Backcourt", 0, x=-9999, y=9999)])
    binned = build_spatial_bins(shots, bins=(12, 10))
    assert binned.loc[0, "bin_x"] == 0
    assert binned.loc[0, "bin_y"] == 9


def test_spatial_bins_missing_column_raises() -> None:
    with pytest.raises(ValueError, match="LOC_X"):
        build_spatial_bins(pd.DataFrame({"LOC_Y": [1]}))


# ---- build_player_season_shot_profile ----------------------------------------


def test_player_profile_zone_frequencies_sum_to_one() -> None:
    profile = build_player_season_shot_profile(_sample_shots(), min_attempts=1)
    freq_cols = [f"{zone}_frequency" for zone in ZONE_FEATURES.values()]
    freq_cols = sorted(set(freq_cols))
    sums = profile[freq_cols].sum(axis=1)
    assert np.allclose(sums, 1.0)


def test_player_profile_exact_values() -> None:
    profile = build_player_season_shot_profile(_sample_shots(), min_attempts=2)

    assert len(profile) == 1  # player 2 excluded by min_attempts
    row = profile.iloc[0]
    assert row["player_id"] == 1
    assert row["player_name"] == "Player 1"
    assert row["team_id"] == 1
    assert row["season"] == "2025-26"
    assert row["total_attempts"] == 4

    assert row["rim_frequency"] == pytest.approx(0.5)
    assert row["midrange_frequency"] == pytest.approx(0.25)
    assert row["corner_three_frequency"] == pytest.approx(0.25)
    assert row["paint_non_rim_frequency"] == pytest.approx(0.0)
    assert row["above_break_three_frequency"] == pytest.approx(0.0)

    assert row["rim_fg_pct"] == pytest.approx(0.5)
    assert row["midrange_fg_pct"] == pytest.approx(1.0)
    assert row["corner_three_fg_pct"] == pytest.approx(1.0)
    assert math.isnan(row["paint_non_rim_fg_pct"])

    # (1 made 2PT * 2 + 1 made 2PT * 2 ... ) -> made: rim 2pts + mid 2pts + corner 3pts = 7 / 4
    assert row["points_per_shot"] == pytest.approx(7 / 4)
    assert row["average_shot_distance"] == pytest.approx((1 + 2 + 16 + 23) / 4)


def test_player_profile_entropy_bounds() -> None:
    # All shots in the same spot -> entropy 0.
    concentrated = pd.DataFrame([_shot(1, "Restricted Area", 1, x=0, y=10)] * 10)
    profile = build_player_season_shot_profile(concentrated, min_attempts=1)
    assert profile.iloc[0]["shot_entropy"] == pytest.approx(0.0)

    # Shots spread over many distinct bins -> entropy strictly higher.
    xs = np.linspace(-240, 240, 12, dtype=int)
    spread = pd.DataFrame([_shot(1, "Mid-Range", 1, x=int(x), y=200) for x in xs])
    spread_profile = build_player_season_shot_profile(spread, min_attempts=1)
    assert spread_profile.iloc[0]["shot_entropy"] > 0.3


def test_player_profile_bin_frequencies_normalized() -> None:
    profile = build_player_season_shot_profile(_sample_shots(), min_attempts=1, bins=(4, 3))
    bin_cols = [c for c in profile.columns if c.startswith("bin_")]
    assert len(bin_cols) == 12
    assert np.allclose(profile[bin_cols].sum(axis=1), 1.0)


def test_player_profile_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        build_player_season_shot_profile(pd.DataFrame())


def test_player_profile_missing_columns_raise() -> None:
    with pytest.raises(ValueError, match="SHOT_ZONE_BASIC"):
        build_player_season_shot_profile(
            _sample_shots().drop(columns=["SHOT_ZONE_BASIC"]), min_attempts=1
        )


def test_player_profile_deterministic() -> None:
    a = build_player_season_shot_profile(_sample_shots(), min_attempts=1)
    b = build_player_season_shot_profile(_sample_shots(), min_attempts=1)
    pd.testing.assert_frame_equal(a, b)


# ---- team profiles -----------------------------------------------------------


def test_team_profile_aggregates_by_team() -> None:
    shots = pd.concat(
        [
            _sample_shots(),
            pd.DataFrame([_shot(3, "Restricted Area", 1, team=2) for _ in range(3)]),
        ],
        ignore_index=True,
    )
    profile = build_team_season_shot_profile(shots, min_attempts=3)
    assert set(profile["team_id"]) == {1, 2}
    team2 = profile.loc[profile["team_id"] == 2].iloc[0]
    assert team2["rim_frequency"] == pytest.approx(1.0)
    assert team2["total_attempts"] == 3


def test_team_window_profile_pools_recent_seasons() -> None:
    old = pd.DataFrame([_shot(1, "Mid-Range", 0, season="2021-22") for _ in range(5)])
    recent = pd.DataFrame(
        [_shot(1, "Restricted Area", 1, season=s) for s in ("2023-24", "2024-25", "2025-26")] * 2
    )
    shots = pd.concat([old, recent], ignore_index=True)

    windowed = build_team_window_profile(shots, seasons_back=3, min_attempts=1)
    row = windowed.iloc[0]
    # Only the 3 most recent seasons pooled -> all rim, the 2021-22 midrange ignored.
    assert row["rim_frequency"] == pytest.approx(1.0)
    assert row["total_attempts"] == 6
    assert row["season"] == "2023-24:2025-26"


def test_court_bounds_constant_shape() -> None:
    x_min, x_max, y_min, y_max = COURT_BOUNDS
    assert x_min < x_max and y_min < y_max
