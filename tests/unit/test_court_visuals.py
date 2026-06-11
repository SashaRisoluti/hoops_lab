"""Unit tests for the matplotlib court, shot maps and spatial heatmaps."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from hoops_lab.features.shot_spatial_features import COURT_BOUNDS  # noqa: E402
from hoops_lab.visuals.court import draw_court  # noqa: E402
from hoops_lab.visuals.heatmaps import (  # noqa: E402
    centroid_heatmap,
    compute_efficiency_grid,
    shot_density_heatmap,
    shot_efficiency_heatmap,
)
from hoops_lab.visuals.shot_maps import player_shot_map, team_shot_map  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _shots(n: int = 50, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "LOC_X": rng.integers(-240, 240, n),
            "LOC_Y": rng.integers(-40, 400, n),
            "SHOT_MADE_FLAG": rng.integers(0, 2, n),
            "PLAYER_NAME": "Test Player",
        }
    )


# ---- court -------------------------------------------------------------------


def test_draw_court_returns_figure_and_axes() -> None:
    fig, ax = draw_court()
    assert fig is not None and ax is not None
    x_min, x_max, y_min, y_max = COURT_BOUNDS
    assert ax.get_xlim() == (x_min, x_max)
    assert len(ax.lines) + len(ax.patches) > 5  # hoop, paint, arcs...


def test_draw_court_on_existing_axes() -> None:
    fig, ax = plt.subplots()
    fig2, ax2 = draw_court(ax=ax)
    assert ax2 is ax and fig2 is fig


# ---- shot maps ---------------------------------------------------------------


def test_player_shot_map_returns_figure() -> None:
    fig = player_shot_map(_shots(), title="Test Player")
    assert fig is not None
    assert len(fig.axes) == 1


def test_player_shot_map_empty_dataframe_is_graceful() -> None:
    fig = player_shot_map(pd.DataFrame(columns=["LOC_X", "LOC_Y", "SHOT_MADE_FLAG"]))
    assert fig is not None  # empty court + note, no crash


def test_player_shot_map_missing_columns_raise() -> None:
    with pytest.raises(ValueError, match="LOC_Y"):
        player_shot_map(pd.DataFrame({"LOC_X": [0]}))


def test_team_shot_map_subsamples_deterministically() -> None:
    shots = _shots(n=500)
    fig1 = team_shot_map(shots, max_points=100)
    fig2 = team_shot_map(shots, max_points=100)
    pts1 = fig1.axes[0].collections[-1].get_offsets()
    pts2 = fig2.axes[0].collections[-1].get_offsets()
    assert np.array_equal(np.asarray(pts1), np.asarray(pts2))


# ---- heatmaps ----------------------------------------------------------------


def test_density_heatmap_returns_figure() -> None:
    fig = shot_density_heatmap(_shots(200))
    assert fig is not None


def test_efficiency_grid_masks_low_attempts() -> None:
    # 10 attempts (6 made) in one spot, a single attempt elsewhere.
    rows = [{"LOC_X": 0, "LOC_Y": 10, "SHOT_MADE_FLAG": int(i < 6)} for i in range(10)]
    rows.append({"LOC_X": 240, "LOC_Y": 400, "SHOT_MADE_FLAG": 1})
    shots = pd.DataFrame(rows)

    eff, attempts = compute_efficiency_grid(shots, bins=(12, 10), min_attempts=5)
    assert eff.shape == (10, 12) and attempts.shape == (10, 12)
    assert attempts.sum() == 11
    assert np.nanmax(eff) == pytest.approx(0.6)  # the qualified cell
    assert np.isnan(eff[attempts == 1]).all()  # below min_attempts -> masked


def test_efficiency_heatmap_returns_figure() -> None:
    fig = shot_efficiency_heatmap(_shots(300), min_attempts=1)
    assert fig is not None


def test_efficiency_heatmap_empty_is_graceful() -> None:
    fig = shot_efficiency_heatmap(
        pd.DataFrame(columns=["LOC_X", "LOC_Y", "SHOT_MADE_FLAG"]), min_attempts=1
    )
    assert fig is not None


def test_centroid_heatmap_from_bin_vector() -> None:
    freqs = np.zeros(120)
    freqs[13] = 0.7
    freqs[100] = 0.3
    fig = centroid_heatmap(freqs, bins=(12, 10), title="Rim Pressure")
    assert fig is not None


def test_centroid_heatmap_wrong_length_raises() -> None:
    with pytest.raises(ValueError, match="120"):
        centroid_heatmap(np.zeros(7), bins=(12, 10))
