"""Advanced stats computed from box-score counts: TS%, eFG%, rates, ratios.

Every function takes a DataFrame and returns an enriched copy; computed
columns carry the ``_CALC`` suffix to distinguish them from endpoint-provided
values (e.g. ``TS_PCT`` in ``advanced_player_stats``), which lets the
integration suite cross-validate our formulas against nba_api's numbers.

Model-based impact metrics (PER, BPM, VORP, On/Off) are NOT re-implemented
here: league-adjusted models need careful calibration and arrive with
Phase 6; until then the dashboard uses the endpoint-provided values already
ingested in ``advanced_player_stats``.

Column-name defaults follow nba_api conventions (PTS, FGM, FGA, FG3M, FG3A,
FTA, AST, TOV).
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.traditional import FT_POSSESSION_WEIGHT, _safe_div


def true_shooting_pct(
    df: pd.DataFrame,
    pts_col: str = "PTS",
    fga_col: str = "FGA",
    fta_col: str = "FTA",
    out_col: str = "TS_PCT_CALC",
) -> pd.DataFrame:
    """Add True Shooting %: ``PTS / (2 * (FGA + 0.44 * FTA))`` (0-1 fraction)."""
    out = df.copy()
    out[out_col] = _safe_div(
        out[pts_col], 2.0 * (out[fga_col] + FT_POSSESSION_WEIGHT * out[fta_col])
    )
    return out


def effective_fg_pct(
    df: pd.DataFrame,
    fgm_col: str = "FGM",
    fg3m_col: str = "FG3M",
    fga_col: str = "FGA",
    out_col: str = "EFG_PCT_CALC",
) -> pd.DataFrame:
    """Add effective FG%: ``(FGM + 0.5 * FG3M) / FGA`` (0-1 fraction)."""
    out = df.copy()
    out[out_col] = _safe_div(out[fgm_col] + 0.5 * out[fg3m_col], out[fga_col])
    return out


def three_point_attempt_rate(
    df: pd.DataFrame,
    fg3a_col: str = "FG3A",
    fga_col: str = "FGA",
    out_col: str = "FG3A_RATE_CALC",
) -> pd.DataFrame:
    """Add the share of field-goal attempts taken from three: ``FG3A / FGA``."""
    out = df.copy()
    out[out_col] = _safe_div(out[fg3a_col], out[fga_col])
    return out


def free_throw_rate(
    df: pd.DataFrame,
    fta_col: str = "FTA",
    fga_col: str = "FGA",
    out_col: str = "FTR_CALC",
) -> pd.DataFrame:
    """Add free-throw rate: ``FTA / FGA``."""
    out = df.copy()
    out[out_col] = _safe_div(out[fta_col], out[fga_col])
    return out


def assist_to_turnover(
    df: pd.DataFrame,
    ast_col: str = "AST",
    tov_col: str = "TOV",
    out_col: str = "AST_TO_CALC",
) -> pd.DataFrame:
    """Add assist-to-turnover ratio: ``AST / TOV`` (NaN when TOV is 0)."""
    out = df.copy()
    out[out_col] = _safe_div(out[ast_col], out[tov_col])
    return out


def turnover_pct(
    df: pd.DataFrame,
    tov_col: str = "TOV",
    fga_col: str = "FGA",
    fta_col: str = "FTA",
    out_col: str = "TOV_PCT_CALC",
) -> pd.DataFrame:
    """Add turnover %: ``100 * TOV / (FGA + 0.44 * FTA + TOV)``."""
    out = df.copy()
    out[out_col] = _safe_div(
        100.0 * out[tov_col],
        out[fga_col] + FT_POSSESSION_WEIGHT * out[fta_col] + out[tov_col],
    )
    return out


def add_advanced_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Apply every advanced stat with default column names in one pass."""
    out = true_shooting_pct(df)
    out = effective_fg_pct(out)
    out = three_point_attempt_rate(out)
    out = free_throw_rate(out)
    out = assist_to_turnover(out)
    out = turnover_pct(out)
    return out
