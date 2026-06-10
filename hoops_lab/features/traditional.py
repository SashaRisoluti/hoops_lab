"""Traditional-stat normalisation: per game, per 36 minutes, per 100 possessions.

Every function takes a DataFrame and returns an **enriched copy** (the input
is never mutated); new columns get an explicit suffix. Division by zero
yields NaN, never inf.
"""

from __future__ import annotations

import pandas as pd

#: Coefficient for free-throw possessions in the classic estimate.
FT_POSSESSION_WEIGHT = 0.44


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise division returning NaN where the denominator is <= 0."""
    return numerator / denominator.where(denominator > 0)


def per_game(
    df: pd.DataFrame,
    cols: list[str],
    games_col: str = "GP",
    suffix: str = "_PG",
) -> pd.DataFrame:
    """Add per-game versions of total columns.

    Parameters
    ----------
    df:
        Input data with total stats.
    cols:
        Columns to normalise (e.g. ``["PTS", "REB", "AST"]``).
    games_col:
        Column holding games played.
    suffix:
        Suffix for the new columns (``PTS`` -> ``PTS_PG``).
    """
    out = df.copy()
    for col in cols:
        out[f"{col}{suffix}"] = _safe_div(out[col], out[games_col])
    return out


def per_36(
    df: pd.DataFrame,
    cols: list[str],
    minutes_col: str = "MIN",
    suffix: str = "_PER36",
) -> pd.DataFrame:
    """Add per-36-minutes versions of stat columns (pace-free comparison)."""
    out = df.copy()
    for col in cols:
        out[f"{col}{suffix}"] = _safe_div(out[col] * 36.0, out[minutes_col])
    return out


def estimate_possessions(
    df: pd.DataFrame,
    fga_col: str = "FGA",
    fta_col: str = "FTA",
    oreb_col: str = "OREB",
    tov_col: str = "TOV",
    out_col: str = "POSS_EST",
) -> pd.DataFrame:
    """Add the classic possession estimate.

    ``POSS ~= FGA + 0.44 * FTA - OREB + TOV`` — the simple single-team form
    (Oliver's full formula averages the two teams; good enough for MVP-level
    pace and per-possession normalisation, refined in Phase 4 from
    play-by-play data).
    """
    out = df.copy()
    out[out_col] = out[fga_col] + FT_POSSESSION_WEIGHT * out[fta_col] - out[oreb_col] + out[tov_col]
    return out


def per_100_possessions(
    df: pd.DataFrame,
    cols: list[str],
    poss_col: str = "POSS_EST",
    suffix: str = "_PER100",
) -> pd.DataFrame:
    """Add per-100-possessions versions of stat columns (pace-adjusted)."""
    out = df.copy()
    for col in cols:
        out[f"{col}{suffix}"] = _safe_div(out[col] * 100.0, out[poss_col])
    return out
