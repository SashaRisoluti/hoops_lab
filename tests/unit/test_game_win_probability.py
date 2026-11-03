"""Unit tests for the drifting-lead game win-probability model and its pregame priors."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from hoops_lab.models.game_win_probability import (
    build_states,
    coefficients,
    current_priors,
    expected_calibration_error,
    features,
    fit,
    predict,
    pregame_priors,
    team_game_ratings,
)

A, B, C = 1610612701, 1610612702, 1610612703
TRICODE = {A: "AAA", B: "BBB", C: "CCC"}
HOME, AWAY = A, B
GAME = "0022100001"


def _team_row(
    game_id: str, date: str, season: str, team: int, opp: int, pts: int, opp_pts: int, home: bool
) -> dict:
    """One box_scores_team row whose counting stats estimate 100 possessions."""
    sep = " vs. " if home else " @ "
    return {
        "TEAM_ID": team,
        "TEAM_ABBREVIATION": TRICODE[team],
        "GAME_ID": game_id,
        "GAME_DATE": date,
        "MATCHUP": f"{TRICODE[team]}{sep}{TRICODE[opp]}",
        "PTS": pts,
        "FGA": 90,
        "FTA": 0,
        "OREB": 5,
        "TOV": 15,
        "PLUS_MINUS": pts - opp_pts,
        "season": season,
    }


def _game(
    game_id: str, date: str, season: str, home: int, home_pts: int, away: int, away_pts: int
) -> list[dict]:
    return [
        _team_row(game_id, date, season, home, away, home_pts, away_pts, home=True),
        _team_row(game_id, date, season, away, home, away_pts, home_pts, home=False),
    ]


def _box() -> pd.DataFrame:
    """Three 2021-22 games, then two 2022-23 games of A on the same date."""
    return pd.DataFrame(
        _game("0022100001", "2021-10-20", "2021-22", A, 110, B, 100)
        + _game("0022100002", "2021-10-22", "2021-22", A, 95, C, 105)
        + _game("0022100003", "2021-10-24", "2021-22", A, 102, B, 98)
        + _game("0022200001", "2022-10-19", "2022-23", A, 100, B, 90)
        + _game("0022200002", "2022-10-19", "2022-23", C, 100, A, 80)
    )


def _prior(priors: pd.DataFrame, game_id: str, team: int) -> pd.Series:
    rows = priors[(priors["GAME_ID"] == game_id) & (priors["TEAM_ID"] == team)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_game_possessions_are_the_mean_of_both_team_estimates() -> None:
    box = pd.DataFrame(
        [
            # 90 + 0.44*20 - 10 + 15 = 103.8
            {
                **_team_row(GAME, "2021-10-20", "2021-22", A, B, 110, 100, True),
                "FTA": 20,
                "OREB": 10,
            },
            _team_row(GAME, "2021-10-20", "2021-22", B, A, 100, 110, False),  # 90 - 5 + 15 = 100
        ]
    )
    ratings = team_game_ratings(box).set_index("TEAM_ID")

    assert ratings.loc[A, "poss"] == pytest.approx(101.9)
    assert ratings.loc[B, "poss"] == pytest.approx(101.9)
    assert (ratings.loc[A, "pts"], ratings.loc[A, "opp_pts"]) == (110, 100)
    assert (ratings.loc[B, "pts"], ratings.loc[B, "opp_pts"]) == (100, 110)
    assert ratings.loc[A, "GAME_DATE"] == pd.Timestamp("2021-10-20")


def test_pregame_priors_only_see_earlier_games_of_the_same_season() -> None:
    priors = pregame_priors(_box())

    a_g3 = _prior(priors, "0022100003", A)
    assert a_g3["n_prior"] == 2
    assert a_g3["nr_to_date"] == pytest.approx(0.0)
    assert a_g3["prior"] == pytest.approx(0.0)

    b_g3 = _prior(priors, "0022100003", B)
    assert b_g3["n_prior"] == 1
    assert b_g3["nr_to_date"] == pytest.approx(-10.0)
    assert b_g3["prior"] == pytest.approx(-10 / 11)

    a_g1 = _prior(priors, "0022100001", A)
    assert a_g1["n_prior"] == 0
    assert a_g1["prior"] == pytest.approx(0.0)


def test_pregame_prior_falls_back_on_last_season_final_net_rating() -> None:
    priors = pregame_priors(_box())
    last_season = 100 * (10 - 10 + 4) / 300  # A's 2021-22 final net rating

    first = _prior(priors, "0022200001", A)
    assert first["n_prior"] == 0
    assert first["nr_last_season"] == pytest.approx(last_season)
    assert first["prior"] == pytest.approx(last_season)

    # Same date as the first game: the strict "<" check keeps it out.
    same_day = _prior(priors, "0022200002", A)
    assert same_day["n_prior"] == 0
    assert same_day["prior"] == pytest.approx(last_season)


def test_current_priors_include_every_game_of_the_season() -> None:
    priors, as_of = current_priors(_box(), "2021-22")

    assert priors["AAA"] == pytest.approx((3 * 100 * 4 / 300 + 10 * 0) / 13)  # ~0.307692
    assert priors["AAA"] == pytest.approx(0.307692, abs=1e-6)
    assert as_of == "2021-10-24"


def _pbp(rows: list[tuple]) -> pd.DataFrame:
    """PBPv3 rows: (actionNumber, period, clock, teamId, actionType, description, shotValue)."""
    frame = pd.DataFrame(
        rows,
        columns=[
            "actionNumber",
            "period",
            "clock",
            "teamId",
            "actionType",
            "description",
            "shotValue",
        ],
    )
    frame["gameId"] = GAME
    frame["location"] = frame["teamId"].map({HOME: "h", AWAY: "v"}).fillna("")
    frame["scoreHome"] = "99"  # deliberately wrong: the margin must come from scoring events
    frame["scoreAway"] = "0"
    frame["season"] = "2021-22"
    return frame


def _games(neutral: bool = False) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": [GAME],
            "season": ["2021-22"],
            "season_type": ["Regular Season"],
            "game_date": [pd.Timestamp("2021-10-20").date()],
            "home_team_id": [HOME],
            "away_team_id": [AWAY],
            "home_pts": [100],
            "away_pts": [90],
            "neutral_site": [neutral],
        }
    )


def _state_priors() -> pd.DataFrame:
    return pd.DataFrame({"GAME_ID": [GAME, GAME], "TEAM_ID": [HOME, AWAY], "prior": [3.0, -1.0]})


def test_build_states_sums_scoring_events_and_ignores_score_snapshots() -> None:
    pbp = _pbp(
        [
            (1, 1, "PT12M00.00S", 0, "period", "Start of 1st Period", 0),
            (2, 1, "PT11M00.00S", HOME, "Made Shot", "Home 20' Jump Shot (2 PTS)", 2),
            (3, 1, "PT10M30.00S", AWAY, "Free Throw", "Away Free Throw 1 of 2 (1 PTS)", 0),
            (4, 1, "PT10M30.00S", AWAY, "Free Throw", "MISS Away Free Throw 2 of 2", 0),
        ]
    ).iloc[::-1]  # rows arrive out of order: build_states sorts them chronologically
    states = build_states(pbp, _games(), _state_priors())

    assert list(zip(states["margin"], states["seconds_remaining"], strict=True)) == [
        (0, 2880),
        (2, 2820),
        (1, 2790),
    ]
    assert (states["game_id"] == GAME).all()
    assert (states["season"] == "2021-22").all()
    assert (states["prior_diff"] == 4.0).all()
    assert states["home_won"].all()
    assert not states["neutral"].any()


def test_overtime_counts_down_the_extra_period_only() -> None:
    pbp = _pbp([(9, 5, "PT04M58.00S", HOME, "Made Shot", "Home Layup (2 PTS)", 2)])
    states = build_states(pbp, _games(neutral=True), _state_priors())

    assert states["seconds_remaining"].tolist() == [2880, 298]
    assert states["neutral"].all()


def test_features_are_drifting_lead_terms() -> None:
    states = pd.DataFrame(
        {
            "margin": [6, 6, 6],
            "seconds_remaining": [720, 720, 0],
            "neutral": [False, True, False],
            "prior_diff": [4.0, 4.0, 4.0],
        }
    )
    x = features(states)

    assert x[0] == pytest.approx([12.0, 0.5, 2.0])
    assert x[1][1] == 0.0
    root = np.sqrt(1 / 2880)  # f floors at one second, never zero
    assert x[2] == pytest.approx([6 / root, root, 4 * root])
    assert np.isfinite(x).all()


def test_fit_recovers_known_coefficients() -> None:
    rng = np.random.default_rng(7)
    n = 20_000
    states = pd.DataFrame(
        {
            "margin": rng.integers(-20, 21, n),
            "seconds_remaining": rng.uniform(0, 2880, n),
            "neutral": rng.random(n) < 0.1,
            "prior_diff": rng.normal(0, 5, n),
        }
    )
    z = features(states) @ np.array([0.1, 0.3, 0.05])
    states["home_won"] = rng.random(n) < 1 / (1 + np.exp(-z))

    model = fit(states)
    fitted = coefficients(model)

    assert fitted["a"] == pytest.approx(0.1, abs=0.02)
    assert fitted["b"] == pytest.approx(0.3, abs=0.1)
    assert fitted["c"] == pytest.approx(0.05, abs=0.02)
    p = predict(model, states)
    assert p.shape == (n,)
    assert ((p >= 0) & (p <= 1)).all()  # late big leads saturate to exactly 0/1 in float


def test_expected_calibration_error() -> None:
    y = np.array([1, 0, 1, 1])
    p = np.array([0.9, 0.1, 0.8, 0.3])

    assert expected_calibration_error(y, p) == pytest.approx(0.275)


def test_coefficients_report_readable_parameters() -> None:
    model = LogisticRegression()
    model.coef_ = np.array([[0.1, 0.3, 0.05]])

    readable = coefficients(model)

    assert readable["a"] == pytest.approx(0.1)
    assert readable["homeCourtPts"] == pytest.approx(3.0)
    assert readable["pointsPerNetRating"] == pytest.approx(0.5)
    assert readable["scale"] == pytest.approx(10.0)


def test_inputs_are_not_mutated() -> None:
    box = _box()
    pbp = _pbp([(2, 1, "PT11M00.00S", HOME, "Made Shot", "Home Jump Shot (2 PTS)", 2)])
    games, priors = _games(), _state_priors()
    originals = [frame.copy() for frame in (box, pbp, games, priors)]

    team_game_ratings(box)
    pregame_priors(box)
    current_priors(box, "2021-22")
    states = build_states(pbp, games, priors)
    states_copy = states.copy()
    features(states)

    for frame, original in zip((box, pbp, games, priors), originals, strict=True):
        pd.testing.assert_frame_equal(frame, original)
    pd.testing.assert_frame_equal(states, states_copy)
