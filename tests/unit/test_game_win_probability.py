"""Unit tests for the drifting-lead game win-probability model and its pregame priors."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

import scripts.export_web_data as export
from hoops_lab.models.game_win_probability import (
    STATE_COLUMNS,
    build_states,
    clipped_log_loss,
    coefficients,
    completed_holdout_seasons,
    current_priors,
    evaluate_holdout,
    expected_calibration_error,
    features,
    fit,
    gate_passes,
    predict,
    pregame_priors,
    pregame_states,
    team_game_ratings,
)
from hoops_lab.storage.database import Database

A, B, C, D = 1610612701, 1610612702, 1610612703, 1610612704
TRICODE = {A: "AAA", B: "BBB", C: "CCC", D: "DDD"}
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


def test_current_priors_keep_teams_that_have_not_played_yet() -> None:
    box = _box()
    box = box[box["GAME_ID"] != "0022200002"]  # in 2022-23 only A and B have played
    priors, as_of = current_priors(box, "2022-23")

    assert set(priors) == {"AAA", "BBB", "CCC"}
    assert priors["CCC"] == pytest.approx(10.0)  # n = 0: C's 2021-22 final net rating
    assert priors["AAA"] == pytest.approx((1 * 10 + 10 * 4 / 3) / 11)
    assert priors["BBB"] == pytest.approx((1 * -10 + 10 * -7) / 11)
    assert as_of == "2022-10-19"


def test_current_priors_of_a_season_without_games_are_last_season_finals() -> None:
    priors, as_of = current_priors(_box(), "2023-24")

    # 2022-23 finals: A +10 and -20 over 200 poss, B -10 and C +20 over 100.
    assert priors == pytest.approx({"AAA": -5.0, "BBB": -10.0, "CCC": 20.0})
    assert as_of == "2022-10-19"


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


def test_scoring_event_of_neither_side_is_skipped() -> None:
    pbp = _pbp(
        [
            (2, 1, "PT11M00.00S", HOME, "Made Shot", "Home Jump Shot (2 PTS)", 2),
            (3, 1, "PT10M00.00S", C, "Made Shot", "Stray Layup (2 PTS)", 2),
            (4, 1, "PT09M00.00S", 0, "Made Shot", "Teamless Layup (2 PTS)", 2),
        ]
    )
    states = build_states(pbp, _games(), _state_priors())

    assert states["margin"].tolist() == [0, 2]
    assert states["seconds_remaining"].tolist() == [2880, 2820]


def test_build_states_without_events_is_an_empty_frame() -> None:
    states = build_states(_pbp([]), _games(), _state_priors())

    assert states.empty
    assert list(states.columns) == STATE_COLUMNS


def test_pregame_states_open_every_game_with_both_priors() -> None:
    states = pregame_states(_games(neutral=True), _state_priors())

    assert list(states.columns) == STATE_COLUMNS
    row = states.iloc[0]
    assert (row["margin"], row["seconds_remaining"]) == (0, 2880)
    assert (row["prior_diff"], row["neutral"], row["home_won"]) == (4.0, True, True)


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


def test_clipped_log_loss_stays_finite_on_certain_predictions() -> None:
    y = np.array([1, 0, 1])
    p = np.array([1.0, 0.0, 0.5])

    assert clipped_log_loss(y, p) == pytest.approx(np.log(2) / 3)
    assert np.isfinite(clipped_log_loss(np.array([0]), np.array([1.0])))


_PASSING = {
    "holdoutLogLoss": 0.45,
    "baselineLogLoss": 0.50,
    "ece": 0.05,
    "pregameLogLoss": 0.66,
    "constantLogLoss": 0.69,
}


@pytest.mark.parametrize(
    ("change", "passes"),
    [
        ({}, True),
        ({"holdoutLogLoss": 0.50}, False),  # must beat the baseline strictly
        ({"ece": 0.0501}, False),
        ({"pregameLogLoss": 0.69}, False),  # must beat the constant strictly
        ({"ece": float("nan")}, False),
    ],
)
def test_gate_passes_truth_table(change: dict, passes: bool) -> None:
    assert gate_passes({**_PASSING, **change}) is passes


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


# ---- temporal holdout -------------------------------------------------------

#: season -> (date, home won A-B, home won C-D). Both games of a season share the date.
_SEASONS = {
    "2021-22": ("2021-10-20", True, False),
    "2022-23": ("2022-10-20", True, False),
    "2023-24": ("2023-10-20", True, True),
}


def _wp_db() -> Database:
    """Three seasons of two games (A hosts B, C hosts D); the home side scores first."""
    box, games, pbp = [], [], []
    for i, (season, (date, *home_won)) in enumerate(_SEASONS.items()):
        for j, ((home, away), won) in enumerate(zip([(A, B), (C, D)], home_won, strict=True)):
            game_id = f"00{i}{j}"
            home_pts, away_pts = (110, 100) if won else (100, 110)
            box += _game(game_id, date, season, home, home_pts, away, away_pts)
            games.append(
                {
                    "game_id": game_id,
                    "season": season,
                    "season_type": "Regular Season",
                    "home_team_id": home,
                    "away_team_id": away,
                    "home_pts": home_pts,
                    "away_pts": away_pts,
                    "neutral_site": False,
                }
            )
            pbp.append(
                {
                    "gameId": game_id,
                    "actionNumber": 1,
                    "period": 1,
                    "clock": "PT11M00.00S",
                    "teamId": home,
                    "actionType": "Made Shot",
                    "description": "Home Jump Shot (2 PTS)",
                    "shotValue": 2,
                }
            )
    db = Database(path=":memory:")
    for name, rows in (("box_scores_team", box), ("games", games), ("play_by_play", pbp)):
        db.connect().register(name, pd.DataFrame(rows))
    return db


def test_holdout_trains_only_on_seasons_before_the_held_out_ones() -> None:
    metrics = evaluate_holdout(_wp_db(), ["2022-23"])

    # 2023-24 is newer than the held-out season: it neither trains nor sets the home rate.
    assert (metrics["trainGames"], metrics["holdoutGames"]) == (2, 2)
    assert metrics["constantLogLoss"] == pytest.approx(np.log(2))  # 2021-22 home rate: 1/2


def test_holdout_without_a_split_has_no_metrics_and_fails_the_gate() -> None:
    db = _wp_db()

    assert evaluate_holdout(db, ["2021-22"]) == {}  # nothing older to train on
    assert evaluate_holdout(db, ["2030-31"]) == {}  # no held-out game
    assert evaluate_holdout(db, []) == {}
    assert gate_passes({}) is False


def test_completed_holdout_seasons_are_the_newest_full_regular_seasons() -> None:
    regular = ["2021-22"] * 1230 + ["2022-23"] * 1230 + ["2023-24"] * 1230 + ["2024-25"] * 1229
    games = pd.DataFrame(
        {
            "season": regular + ["2024-25"] * 5,
            # Playoff rows never complete a season.
            "season_type": ["Regular Season"] * len(regular) + ["Playoffs"] * 5,
        }
    )
    db = Database(path=":memory:")
    db.connect().register("games", games)

    assert completed_holdout_seasons(db) == ["2022-23", "2023-24"]
    assert completed_holdout_seasons(db, n=1) == ["2023-24"]


# ---- web export of the model ------------------------------------------------

_GATE_METRICS = {"trainGames": 2, "holdoutGames": 2, **_PASSING}


def test_export_withholds_a_model_that_fails_its_gate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failing = {**_GATE_METRICS, "ece": 0.08}
    monkeypatch.setattr(export, "evaluate_holdout", lambda db, held_out: failing)

    model = export.build_win_probability(_wp_db())

    assert model == {"available": False, "metrics": {**failing, "fitGames": 6}}
    assert "win probability gate FAIL" in capsys.readouterr().out


def test_export_drops_metrics_that_are_not_finite(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = {**_GATE_METRICS, "ece": float("nan")}
    monkeypatch.setattr(export, "evaluate_holdout", lambda db, held_out: broken)

    assert export.build_win_probability(_wp_db()) == {"available": False}


def test_export_without_a_completed_season_is_unavailable_and_never_nan(
    capsys: pytest.CaptureFixture[str],
) -> None:
    model = export.build_win_probability(_wp_db())  # no season has 1230 games

    assert model == {"available": False}
    json.dumps(model, allow_nan=False)
    assert "win probability gate FAIL" in capsys.readouterr().out


def test_export_ships_the_full_refit_with_last_season_priors_at_rollover(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(export, "evaluate_holdout", lambda db, held_out: _GATE_METRICS)
    # The newest configured season has no game yet: its priors are 2023-24's finals.
    monkeypatch.setattr(export, "DEMO_SEASONS", [*_SEASONS, "2024-25"])

    model = export.build_win_probability(_wp_db())

    assert model["available"] is True
    assert model["season"] == "2024-25"
    assert model["asOf"] == "2023-10-20"
    assert model["teams"] == {"AAA": 10.0, "BBB": -10.0, "CCC": 10.0, "DDD": -10.0}
    assert model["metrics"] == {**_GATE_METRICS, "fitGames": 6}
    assert "win probability gate PASS" in capsys.readouterr().out
