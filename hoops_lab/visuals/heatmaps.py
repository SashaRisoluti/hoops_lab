"""Spatial heatmaps on the half court: density, efficiency, cluster centroids.

The efficiency grid applies a ``min_attempts`` mask so near-empty cells do
not show noisy 0% / 100% values. The centroid heatmap turns the ``bin_###``
frequency vector of an archetype (mean of its members) back into a court
picture — the visual identity of a KMeans cluster.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from hoops_lab.features.shot_spatial_features import COURT_BOUNDS, build_spatial_bins
from hoops_lab.visuals.court import COURT_BG, draw_court

#: Hex literals mirrored from ``dashboard.components.theme`` tokens (no dashboard
#: import here — ``hoops_lab`` must never import from ``dashboard``).
RAMP_COLD = "#0052ff"
RAMP_HOT = "#ffd100"
EFF_WEAK = "#e0262c"
EFF_MID = "#ffd100"
EFF_GOOD = "#16c47f"
TEXT_SOFT = "#9ca3af"
TEXT_MAIN = "#f1f5f9"

#: Navy-to-yellow ramp for frequency/density surfaces (cold -> hot).
DENSITY_CMAP = LinearSegmentedColormap.from_list("hoops_density", [COURT_BG, RAMP_COLD, RAMP_HOT])
#: Red-yellow-green ramp for efficiency surfaces (weak -> mid -> good).
EFFICIENCY_CMAP = LinearSegmentedColormap.from_list(
    "hoops_efficiency", [EFF_WEAK, EFF_MID, EFF_GOOD]
)


def _grid_extent() -> tuple[float, float, float, float]:
    x_min, x_max, y_min, y_max = COURT_BOUNDS
    return x_min, x_max, y_min, y_max


def _empty_court(title: str | None) -> Figure:
    fig, ax = draw_court()
    ax.text(0, 200, "No shots to plot", ha="center", color=TEXT_SOFT, fontsize=11)
    if title:
        ax.set_title(title, color=TEXT_SOFT)
    return fig


def shot_density_heatmap(
    shots_df: pd.DataFrame,
    title: str | None = None,
    bins: tuple[int, int] = (24, 20),
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
) -> Figure:
    """Shot-frequency surface over the half court.

    Args:
        shots_df: One row per shot.
        title: Optional title.
        bins: Histogram grid (n_x, n_y).
        x_col: X coordinate column.
        y_col: Y coordinate column.

    Returns:
        A matplotlib Figure (annotated empty court for an empty frame).

    Raises:
        ValueError: If a coordinate column is missing.
    """
    if shots_df.empty:
        return _empty_court(title)
    binned = build_spatial_bins(shots_df, x_col=x_col, y_col=y_col, bins=bins)
    counts = np.zeros((bins[1], bins[0]))
    cell_counts = binned.groupby(["bin_y", "bin_x"]).size()
    for (by, bx), count in cell_counts.items():
        counts[by, bx] = count

    fig, ax = draw_court()
    ax.imshow(
        counts,
        extent=_grid_extent(),
        origin="lower",
        cmap=DENSITY_CMAP,
        alpha=0.8,
        aspect="auto",
        zorder=0,
    )
    if title:
        ax.set_title(title, color=TEXT_MAIN)
    return fig


def compute_efficiency_grid(
    shots_df: pd.DataFrame,
    bins: tuple[int, int] = (12, 10),
    min_attempts: int = 5,
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
) -> tuple[np.ndarray, np.ndarray]:
    """FG% and attempt-count grids over the half court.

    Args:
        shots_df: One row per shot.
        bins: Grid size (n_x, n_y).
        min_attempts: Cells below this attempt count get NaN FG% (masked).
        x_col: X coordinate column.
        y_col: Y coordinate column.
        made_col: 0/1 make flag column.

    Returns:
        ``(efficiency, attempts)`` arrays of shape (n_y, n_x); efficiency is
        NaN where attempts < ``min_attempts``.

    Raises:
        ValueError: If a required column is missing.
    """
    missing = [c for c in (x_col, y_col, made_col) if c not in shots_df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")

    attempts = np.zeros((bins[1], bins[0]))
    efficiency = np.full((bins[1], bins[0]), np.nan)
    if shots_df.empty:
        return efficiency, attempts

    binned = build_spatial_bins(shots_df, x_col=x_col, y_col=y_col, bins=bins)
    grouped = binned.groupby(["bin_y", "bin_x"])[made_col].agg(["count", "mean"])
    for (by, bx), row in grouped.iterrows():
        attempts[by, bx] = row["count"]
        if row["count"] >= min_attempts:
            efficiency[by, bx] = row["mean"]
    return efficiency, attempts


def shot_efficiency_heatmap(
    shots_df: pd.DataFrame,
    title: str | None = None,
    bins: tuple[int, int] = (12, 10),
    min_attempts: int = 5,
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
) -> Figure:
    """FG% surface over the half court, masking low-volume cells.

    Args:
        shots_df: One row per shot.
        title: Optional title.
        bins: Grid size (n_x, n_y).
        min_attempts: Cells below this attempt count are not colored.
        x_col: X coordinate column.
        y_col: Y coordinate column.
        made_col: 0/1 make flag column.

    Returns:
        A matplotlib Figure with a colorbar (empty court when no shots).
    """
    if shots_df.empty:
        return _empty_court(title)
    efficiency, _ = compute_efficiency_grid(
        shots_df,
        bins=bins,
        min_attempts=min_attempts,
        x_col=x_col,
        y_col=y_col,
        made_col=made_col,
    )
    fig, ax = draw_court()
    image = ax.imshow(
        np.ma.masked_invalid(efficiency),
        extent=_grid_extent(),
        origin="lower",
        cmap=EFFICIENCY_CMAP,
        vmin=0.2,
        vmax=0.7,
        alpha=0.85,
        aspect="auto",
        zorder=0,
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    colorbar.ax.tick_params(colors=TEXT_SOFT, labelsize=8)
    colorbar.set_label("FG%", color=TEXT_SOFT, fontsize=8)
    if title:
        ax.set_title(title, color=TEXT_MAIN)
    return fig


def centroid_heatmap(
    bin_frequencies: np.ndarray | pd.Series,
    bins: tuple[int, int] = (12, 10),
    title: str | None = None,
) -> Figure:
    """Court picture of an archetype's average spatial profile.

    Args:
        bin_frequencies: Flat ``bin_###`` frequency vector (length must be
            n_x * n_y, ordered bin_id = bin_y * n_x + bin_x) — typically the
            mean over the members of one KMeans cluster.
        bins: Grid size (n_x, n_y) the vector was built with.
        title: Optional title (archetype label).

    Returns:
        A matplotlib Figure.

    Raises:
        ValueError: If the vector length does not match the grid.
    """
    values = np.asarray(bin_frequencies, dtype=float)
    expected = bins[0] * bins[1]
    if values.size != expected:
        raise ValueError(f"expected {expected} bin frequencies, got {values.size}")
    grid = values.reshape(bins[1], bins[0])

    fig, ax = draw_court()
    ax.imshow(
        grid,
        extent=_grid_extent(),
        origin="lower",
        cmap=DENSITY_CMAP,
        alpha=0.85,
        aspect="auto",
        zorder=0,
    )
    if title:
        ax.set_title(title, color=TEXT_MAIN)
    return fig
