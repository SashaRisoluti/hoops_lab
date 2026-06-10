"""Tactical alert rules: turn the live game state into operational signals.

Each rule is a pure function of (state, baselines); ``evaluate_alerts`` runs
them all. Baselines are season values per team id (see
``live_vs_historical.get_baselines``).
"""

from __future__ import annotations

from pydantic import BaseModel

from hoops_lab.live.game_state import GameState

#: Rule thresholds (kept in one place for tuning).
RUN_WINDOW = 8
RUN_THRESHOLD = 8
TOV_WINDOW = 6
TOV_THRESHOLD = 3
COLD_MIN_FGA = 15
COLD_EFG_GAP = 0.10
PACE_MIN_MINUTES = 8.0
PACE_GAP = 8.0


class Alert(BaseModel):
    """One tactical alert."""

    rule: str
    severity: str  # "info" | "warning"
    message: str


def _team_label(state: GameState, team_id: int) -> str:
    return "HOME" if team_id == state.home_id else "AWAY"


def _scoring_run(state: GameState) -> list[Alert]:
    home_pts, away_pts = state.last_run(RUN_WINDOW)
    swing = home_pts - away_pts
    if abs(swing) < RUN_THRESHOLD:
        return []
    leader = state.home_id if swing > 0 else state.away_id
    points = (max(home_pts, away_pts), min(home_pts, away_pts))
    return [
        Alert(
            rule="scoring_run",
            severity="warning",
            message=(
                f"{_team_label(state, leader)} is on a {points[0]}-{points[1]} run "
                f"over the last {RUN_WINDOW} possessions."
            ),
        )
    ]


def _turnover_trouble(state: GameState) -> list[Alert]:
    alerts = []
    for team_id in (state.home_id, state.away_id):
        count = state.recent_turnovers(team_id, TOV_WINDOW)
        if count >= TOV_THRESHOLD:
            alerts.append(
                Alert(
                    rule="turnover_trouble",
                    severity="warning",
                    message=(
                        f"{_team_label(state, team_id)}: {count} turnovers in the last "
                        f"{TOV_WINDOW} possessions."
                    ),
                )
            )
    return alerts


def _cold_shooting(state: GameState, baselines: dict[int, dict[str, float]]) -> list[Alert]:
    alerts = []
    for team_id, stats in state.team_stats.items():
        baseline = baselines.get(team_id, {}).get("EFG_PCT")
        live = stats.efg_pct
        if baseline is None or live is None or stats.fga < COLD_MIN_FGA:
            continue
        if live < baseline - COLD_EFG_GAP:
            alerts.append(
                Alert(
                    rule="cold_shooting",
                    severity="info",
                    message=(
                        f"{_team_label(state, team_id)} shooting {live:.1%} eFG vs a "
                        f"{baseline:.1%} season baseline ({stats.fga} FGA)."
                    ),
                )
            )
    return alerts


def _pace_shift(state: GameState, baselines: dict[int, dict[str, float]]) -> list[Alert]:
    live_pace = state.pace_estimate
    if live_pace is None or state.minutes_elapsed < PACE_MIN_MINUTES:
        return []
    season_paces = [baselines[t]["PACE"] for t in (state.home_id, state.away_id) if t in baselines]
    if not season_paces:
        return []
    expected = sum(season_paces) / len(season_paces)
    if abs(live_pace - expected) <= PACE_GAP:
        return []
    direction = "faster" if live_pace > expected else "slower"
    return [
        Alert(
            rule="pace_shift",
            severity="info",
            message=(
                f"Game pace {live_pace:.1f} is much {direction} than the "
                f"{expected:.1f} season expectation."
            ),
        )
    ]


def evaluate_alerts(state: GameState, baselines: dict[int, dict[str, float]]) -> list[Alert]:
    """Run every rule against the current state."""
    alerts: list[Alert] = []
    alerts.extend(_scoring_run(state))
    alerts.extend(_turnover_trouble(state))
    alerts.extend(_cold_shooting(state, baselines))
    alerts.extend(_pace_shift(state, baselines))
    return alerts
