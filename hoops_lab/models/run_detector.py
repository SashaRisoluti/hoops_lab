"""Scoring-run detection over segmented possessions."""

from __future__ import annotations

import pandas as pd

RUN_COLUMNS = [
    "game_id",
    "team_id",
    "start_possession",
    "end_possession",
    "points_for",
    "points_against",
]


def detect_runs(
    possessions: pd.DataFrame,
    window: int = 8,
    threshold: int = 8,
) -> pd.DataFrame:
    """Find one-sided stretches: windows where one team outscores the other.

    A sliding window of ``window`` possessions flags a run when the point
    swing reaches ``threshold``; overlapping windows for the same team are
    merged into a single run with its total points.
    """
    runs: list[dict] = []
    for game_id, game in possessions.groupby("game_id", sort=False):
        game = game.sort_values("possession_number").reset_index(drop=True)
        teams = game["offense_team_id"].unique()
        if len(teams) != 2:
            continue
        team_a, team_b = int(teams[0]), int(teams[1])

        current: dict | None = None
        for start in range(0, len(game) - window + 1):
            chunk = game.iloc[start : start + window]
            pts_a = int(chunk.loc[chunk["offense_team_id"] == team_a, "points"].sum())
            pts_b = int(chunk.loc[chunk["offense_team_id"] == team_b, "points"].sum())
            swing = pts_a - pts_b
            if abs(swing) < threshold:
                continue
            runner = team_a if swing > 0 else team_b
            first = int(chunk.iloc[0]["possession_number"])
            last = int(chunk.iloc[-1]["possession_number"])
            if current and current["team_id"] == runner and first <= current["end_possession"] + 1:
                current["end_possession"] = max(current["end_possession"], last)
            else:
                if current:
                    runs.append(current)
                current = {
                    "game_id": game_id,
                    "team_id": runner,
                    "start_possession": first,
                    "end_possession": last,
                }
        if current:
            runs.append(current)

    if not runs:
        return pd.DataFrame(columns=RUN_COLUMNS)

    # Recompute exact points over each merged span.
    result = []
    for run in runs:
        game = possessions.loc[possessions["game_id"] == run["game_id"]]
        span = game.loc[
            (game["possession_number"] >= run["start_possession"])
            & (game["possession_number"] <= run["end_possession"])
        ]
        points_for = int(span.loc[span["offense_team_id"] == run["team_id"], "points"].sum())
        points_against = int(span.loc[span["offense_team_id"] != run["team_id"], "points"].sum())
        result.append({**run, "points_for": points_for, "points_against": points_against})
    return pd.DataFrame(result, columns=RUN_COLUMNS)
