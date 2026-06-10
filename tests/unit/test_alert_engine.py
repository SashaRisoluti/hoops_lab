"""Unit tests for the tactical alert rules (crafted states, deterministic)."""

from __future__ import annotations

import pandas as pd

from hoops_lab.live.alert_engine import evaluate_alerts
from hoops_lab.live.game_state import GameState, TeamLiveStats

HOME, AWAY = 10, 20


def _possessions(rows: list[tuple[int, int, str]]) -> pd.DataFrame:
    """rows: (offense_team_id, points, ended_by)."""
    return pd.DataFrame(
        {
            "game_id": "g1",
            "possession_number": range(1, len(rows) + 1),
            "offense_team_id": [r[0] for r in rows],
            "period": 4,
            "points": [r[1] for r in rows],
            "ended_by": [r[2] for r in rows],
        }
    )


def _state(
    possessions: pd.DataFrame, home_stats=None, away_stats=None, clock="PT06M00.00S"
) -> GameState:
    return GameState(
        home_id=HOME,
        away_id=AWAY,
        period=2,
        clock=clock,
        score=(50, 48),
        team_stats={HOME: home_stats or TeamLiveStats(), AWAY: away_stats or TeamLiveStats()},
        possessions=possessions,
    )


def _baselines(efg: float = 0.54, pace: float = 99.0) -> dict[int, dict[str, float]]:
    return {
        HOME: {"EFG_PCT": efg, "PACE": pace, "TM_TOV_PCT": 13.0},
        AWAY: {"EFG_PCT": efg, "PACE": pace, "TM_TOV_PCT": 13.0},
    }


def test_scoring_run_alert_fires_on_one_sided_stretch() -> None:
    rows = [(HOME, 2, "made_fg"), (AWAY, 0, "def_rebound")] * 2  # calm start
    rows += [
        (HOME, 3, "made_fg"),
        (AWAY, 0, "def_rebound"),
        (HOME, 2, "made_fg"),
        (AWAY, 0, "turnover"),
        (HOME, 3, "made_fg"),
        (AWAY, 0, "def_rebound"),
        (HOME, 2, "made_fg"),
        (AWAY, 0, "turnover"),
    ]  # last 8: home 10 - away 0
    alerts = evaluate_alerts(_state(_possessions(rows)), _baselines())

    runs = [a for a in alerts if a.rule == "scoring_run"]
    assert len(runs) == 1
    assert "10-0" in runs[0].message
    assert runs[0].severity == "warning"


def test_turnover_trouble_alert() -> None:
    rows = [
        (AWAY, 0, "turnover"),
        (HOME, 2, "made_fg"),
        (AWAY, 0, "turnover"),
        (HOME, 0, "def_rebound"),
        (AWAY, 0, "turnover"),
        (HOME, 2, "made_fg"),
    ]
    alerts = evaluate_alerts(_state(_possessions(rows)), _baselines())

    tov = [a for a in alerts if a.rule == "turnover_trouble"]
    assert len(tov) == 1
    assert "3 turnovers" in tov[0].message.lower()


def test_cold_shooting_alert_needs_sample_and_gap() -> None:
    cold = TeamLiveStats(fgm=5, fga=20, fg3m=1, fg3a=8)  # eFG 0.275 vs 0.54
    alerts = evaluate_alerts(
        _state(_possessions([(HOME, 2, "made_fg")]), home_stats=cold), _baselines(efg=0.54)
    )
    assert any(a.rule == "cold_shooting" for a in alerts)

    small_sample = TeamLiveStats(fgm=1, fga=8)  # below the 15-FGA threshold
    alerts = evaluate_alerts(
        _state(_possessions([(HOME, 2, "made_fg")]), home_stats=small_sample), _baselines()
    )
    assert not any(a.rule == "cold_shooting" for a in alerts)


def test_no_alerts_on_calm_game() -> None:
    rows = [
        (HOME, 2, "made_fg"),
        (AWAY, 2, "made_fg"),
        (HOME, 0, "def_rebound"),
        (AWAY, 3, "made_fg"),
        (HOME, 2, "made_fg"),
        (AWAY, 0, "turnover"),
    ]
    normal = TeamLiveStats(fgm=10, fga=20, fg3m=2, fg3a=6)
    # Pace baseline matched to the live estimate to keep the pace rule quiet.
    state = _state(_possessions(rows), home_stats=normal, away_stats=normal)
    live_pace = state.pace_estimate
    alerts = evaluate_alerts(state, _baselines(pace=live_pace))

    assert alerts == []
