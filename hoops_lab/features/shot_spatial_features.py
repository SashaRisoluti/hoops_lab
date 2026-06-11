"""Spatial shot-profile feature engineering.

Turns raw ShotChartDetail rows (one row per shot) into one numeric profile
vector per player-season (or team-season): zone frequencies, zone efficiency,
spatial-bin frequencies, entropy and diversity. These vectors are the input
of the shot-archetype models (KMeans + SOM) — individual shots are never
clustered directly.

Coordinates follow the ShotChartDetail convention: ``LOC_X``/``LOC_Y`` in
tenths of feet with the origin at the hoop (x in [-250, 250], y from the
baseline behind the hoop to just past half court).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Half-court bounds in ShotChartDetail units: (x_min, x_max, y_min, y_max).
COURT_BOUNDS: tuple[float, float, float, float] = (-250.0, 250.0, -52.5, 417.5)

#: SHOT_ZONE_BASIC -> profile feature key (5 design zones; backcourt heaves
#: are above-the-break threes for profiling purposes).
ZONE_FEATURES: dict[str, str] = {
    "Restricted Area": "rim",
    "In The Paint (Non-RA)": "paint_non_rim",
    "Mid-Range": "midrange",
    "Left Corner 3": "corner_three",
    "Right Corner 3": "corner_three",
    "Above the Break 3": "above_break_three",
    "Backcourt": "above_break_three",
}

#: Ordered unique zone keys (column order of the profile frames).
ZONE_KEYS: list[str] = ["rim", "paint_non_rim", "midrange", "corner_three", "above_break_three"]


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")


def build_spatial_bins(
    shots_df: pd.DataFrame,
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    bins: tuple[int, int] = (12, 10),
    court_bounds: tuple[float, float, float, float] | None = None,
) -> pd.DataFrame:
    """Assign every shot to a cell of a regular half-court grid.

    Args:
        shots_df: One row per shot with coordinate columns.
        x_col: Column with the x location (tenths of feet).
        y_col: Column with the y location (tenths of feet).
        bins: Grid size as (n_bins_x, n_bins_y).
        court_bounds: (x_min, x_max, y_min, y_max); defaults to COURT_BOUNDS.
            Out-of-bounds shots are clipped to the edge cells.

    Returns:
        A copy of ``shots_df`` with ``bin_x``, ``bin_y`` (cell indices) and
        ``bin_id`` (= bin_y * n_bins_x + bin_x) columns appended.
    """
    _require_columns(shots_df, [x_col, y_col])
    x_min, x_max, y_min, y_max = court_bounds or COURT_BOUNDS
    n_x, n_y = bins

    out = shots_df.copy()
    fx = (out[x_col].astype(float) - x_min) / (x_max - x_min)
    fy = (out[y_col].astype(float) - y_min) / (y_max - y_min)
    out["bin_x"] = np.clip(np.floor(fx * n_x), 0, n_x - 1).astype(int)
    out["bin_y"] = np.clip(np.floor(fy * n_y), 0, n_y - 1).astype(int)
    out["bin_id"] = out["bin_y"] * n_x + out["bin_x"]
    return out


def _shot_points(shots: pd.DataFrame, shot_type_col: str = "SHOT_TYPE") -> pd.Series:
    """Point value per attempt (3 for threes, 2 otherwise)."""
    if shot_type_col in shots.columns:
        return shots[shot_type_col].astype(str).str.contains("3PT").map({True: 3, False: 2})
    return pd.Series(2, index=shots.index)


def _profile_one_group(
    shots: pd.DataFrame,
    made_col: str,
    zone_col: str,
    n_bins_total: int,
) -> dict:
    """Profile features for one already-binned player/team group."""
    n = len(shots)
    zones = shots[zone_col].map(ZONE_FEATURES)
    made = shots[made_col].astype(float)
    points = _shot_points(shots)

    features: dict = {"total_attempts": n}

    for key in ZONE_KEYS:
        in_zone = zones == key
        attempts = int(in_zone.sum())
        features[f"{key}_frequency"] = attempts / n
        features[f"{key}_fg_pct"] = float(made[in_zone].mean()) if attempts else float("nan")

    if "SHOT_DISTANCE" in shots.columns:
        features["average_shot_distance"] = float(shots["SHOT_DISTANCE"].mean())
    else:
        dist = np.hypot(shots["LOC_X"].astype(float), shots["LOC_Y"].astype(float)) / 10.0
        features["average_shot_distance"] = float(dist.mean())

    features["points_per_shot"] = float((made * points).sum() / n)

    freqs = np.array([features[f"{key}_frequency"] for key in ZONE_KEYS])
    features["zone_diversity"] = float(1.0 - np.sum(freqs**2))

    # Spatial-bin frequencies + normalized entropy over the full grid.
    bin_counts = shots["bin_id"].value_counts()
    bin_freqs = np.zeros(n_bins_total)
    bin_freqs[bin_counts.index.to_numpy()] = bin_counts.to_numpy() / n
    nonzero = bin_freqs[bin_freqs > 0]
    features["shot_entropy"] = float(-(nonzero * np.log(nonzero)).sum() / np.log(n_bins_total))
    for bin_id, freq in enumerate(bin_freqs):
        features[f"bin_{bin_id:03d}"] = float(freq)
    return features


def _build_profile(
    shots_df: pd.DataFrame,
    group_col: str,
    group_out: str,
    season_col: str,
    x_col: str,
    y_col: str,
    made_col: str,
    zone_col: str,
    min_attempts: int,
    bins: tuple[int, int],
    season_label: str | None = None,
) -> pd.DataFrame:
    """Shared player/team profile builder (one output row per group)."""
    if shots_df.empty:
        raise ValueError("shots_df is empty — nothing to profile")
    _require_columns(shots_df, [group_col, season_col, x_col, y_col, made_col, zone_col])

    binned = build_spatial_bins(shots_df, x_col=x_col, y_col=y_col, bins=bins)
    n_bins_total = bins[0] * bins[1]
    name_col = {"player_id": "PLAYER_NAME", "team_id": "TEAM_NAME"}[group_out]

    rows: list[dict] = []
    for group_id, group in binned.groupby(group_col, sort=True):
        if len(group) < min_attempts:
            continue
        meta: dict = {
            group_out: group_id,
            "season": season_label or str(group[season_col].iloc[0]),
        }
        if name_col in group.columns:
            meta[group_out.replace("_id", "_name")] = str(group[name_col].iloc[0])
        if group_out == "player_id" and "TEAM_ID" in group.columns:
            meta["team_id"] = group["TEAM_ID"].mode().iloc[0]
            if "TEAM_NAME" in group.columns:
                meta["team_name"] = str(group["TEAM_NAME"].mode().iloc[0])
        rows.append(meta | _profile_one_group(group, made_col, zone_col, n_bins_total))

    return pd.DataFrame(rows)


def build_player_season_shot_profile(
    shots_df: pd.DataFrame,
    player_col: str = "PLAYER_ID",
    season_col: str = "season",
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
    zone_col: str = "SHOT_ZONE_BASIC",
    min_attempts: int = 100,
    bins: tuple[int, int] = (12, 10),
) -> pd.DataFrame:
    """One shot-profile vector per player for a single season of shots.

    Args:
        shots_df: All shots of the selected season (league-wide).
        player_col: Player identifier column.
        season_col: Season label column.
        x_col: Shot x location (tenths of feet).
        y_col: Shot y location (tenths of feet).
        made_col: 0/1 make flag column.
        zone_col: SHOT_ZONE_BASIC-style zone column.
        min_attempts: Players below this attempt count are excluded.
        bins: Spatial grid size (n_x, n_y).

    Returns:
        One row per included player: metadata (player_id/name, team_id/name
        by most frequent team, season, total_attempts) plus zone frequencies,
        zone FG%, average distance, points per shot, entropy, diversity and
        normalized ``bin_###`` frequencies.

    Raises:
        ValueError: If ``shots_df`` is empty or a required column is missing.
    """
    return _build_profile(
        shots_df,
        group_col=player_col,
        group_out="player_id",
        season_col=season_col,
        x_col=x_col,
        y_col=y_col,
        made_col=made_col,
        zone_col=zone_col,
        min_attempts=min_attempts,
        bins=bins,
    )


def build_team_season_shot_profile(
    shots_df: pd.DataFrame,
    team_col: str = "TEAM_ID",
    season_col: str = "season",
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
    zone_col: str = "SHOT_ZONE_BASIC",
    min_attempts: int = 500,
    bins: tuple[int, int] = (12, 10),
    season_label: str | None = None,
) -> pd.DataFrame:
    """One shot-profile vector per team (same features as the player profile).

    Args:
        shots_df: All shots of the selected season(s).
        team_col: Team identifier column.
        season_col: Season label column.
        x_col: Shot x location (tenths of feet).
        y_col: Shot y location (tenths of feet).
        made_col: 0/1 make flag column.
        zone_col: SHOT_ZONE_BASIC-style zone column.
        min_attempts: Teams below this attempt count are excluded.
        bins: Spatial grid size (n_x, n_y).
        season_label: Override for the season metadata value (used by the
            multi-season window builder).

    Returns:
        One row per included team with the same feature set as
        :func:`build_player_season_shot_profile`.

    Raises:
        ValueError: If ``shots_df`` is empty or a required column is missing.
    """
    return _build_profile(
        shots_df,
        group_col=team_col,
        group_out="team_id",
        season_col=season_col,
        x_col=x_col,
        y_col=y_col,
        made_col=made_col,
        zone_col=zone_col,
        min_attempts=min_attempts,
        bins=bins,
        season_label=season_label,
    )


def build_team_window_profile(
    shots_df: pd.DataFrame,
    team_col: str = "TEAM_ID",
    season_col: str = "season",
    seasons_back: int = 3,
    aggregation: str = "weighted",
    min_attempts: int = 500,
    bins: tuple[int, int] = (12, 10),
) -> pd.DataFrame:
    """Team profiles over the most recent ``seasons_back`` seasons.

    Args:
        shots_df: Shots spanning one or more seasons.
        team_col: Team identifier column.
        season_col: Season label column (sortable strings like "2023-24").
        seasons_back: How many of the most recent seasons to include.
        aggregation: "weighted" pools all shots of the window (attempt-
            weighted by construction); "mean" averages the per-season
            profile vectors with equal season weights.
        min_attempts: Minimum attempts (per window for "weighted", per
            season for "mean").
        bins: Spatial grid size (n_x, n_y).

    Returns:
        One row per team; ``season`` is labelled "first:last" of the window.

    Raises:
        ValueError: On empty input, missing columns or unknown aggregation.
    """
    if shots_df.empty:
        raise ValueError("shots_df is empty — nothing to profile")
    _require_columns(shots_df, [season_col])

    seasons = sorted(shots_df[season_col].astype(str).unique())[-seasons_back:]
    window = shots_df[shots_df[season_col].astype(str).isin(seasons)]
    label = f"{seasons[0]}:{seasons[-1]}" if len(seasons) > 1 else seasons[0]

    if aggregation == "weighted":
        return build_team_season_shot_profile(
            window,
            team_col=team_col,
            season_col=season_col,
            min_attempts=min_attempts,
            bins=bins,
            season_label=label,
        )
    if aggregation == "mean":
        per_season = [
            build_team_season_shot_profile(
                window[window[season_col].astype(str) == s],
                team_col=team_col,
                season_col=season_col,
                min_attempts=min_attempts,
                bins=bins,
            )
            for s in seasons
        ]
        stacked = pd.concat(per_season, ignore_index=True)
        meta_cols = [c for c in ("team_id", "team_name") if c in stacked.columns]
        numeric = stacked.groupby(meta_cols, sort=True, as_index=False).mean(numeric_only=True)
        numeric["season"] = label
        return numeric
    raise ValueError(f"unknown aggregation: {aggregation!r} (use 'weighted' or 'mean')")
