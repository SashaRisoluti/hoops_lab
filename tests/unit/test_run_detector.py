"""Unit tests for the scoring-run detector (exact crafted possessions)."""

from __future__ import annotations

import pandas as pd

from hoops_lab.models.run_detector import detect_runs

HOME, AWAY = 10, 20


def _possessions(rows: list[tuple[int, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": "g1",
            "possession_number": range(1, len(rows) + 1),
            "offense_team_id": [r[0] for r in rows],
            "period": 1,
            "points": [r[1] for r in rows],
            "ended_by": "made_fg",
        }
    )


def test_detects_and_merges_a_one_sided_run() -> None:
    rows = [
        (HOME, 2),
        (AWAY, 0),
        (HOME, 3),
        (AWAY, 0),
        (HOME, 3),
        (AWAY, 0),  # 8-0 home
        (AWAY, 2),
        (HOME, 2),
        (AWAY, 2),
        (HOME, 0),  # back to normal
    ]
    runs = detect_runs(_possessions(rows), window=6, threshold=8)

    assert len(runs) == 1
    run = runs.iloc[0]
    assert run["team_id"] == HOME
    assert run["points_for"] == 8
    assert run["points_against"] == 0
    assert (run["start_possession"], run["end_possession"]) == (1, 6)


def test_no_runs_in_a_balanced_game() -> None:
    rows = [(HOME, 2), (AWAY, 2), (HOME, 3), (AWAY, 3), (HOME, 2), (AWAY, 2), (HOME, 0), (AWAY, 0)]
    runs = detect_runs(_possessions(rows), window=6, threshold=8)
    assert runs.empty
