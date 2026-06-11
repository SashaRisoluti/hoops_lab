"""Unit tests for the Self-Organizing Map over shot-profile vectors.

The SOM is fitted on the same standardized matrix as KMeans; tests check
grid-coordinate validity, reproducibility with a fixed seed, topology
(similar profiles land close), and small-dataset handling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hoops_lab.models.shot_som import (
    assign_som_coordinates,
    auto_grid_size,
    fit_shot_profile_som,
    summarize_som_map,
)


def _matrix(per_group: int = 12, seed: int = 3) -> tuple[np.ndarray, pd.DataFrame]:
    """Two well-separated blobs in 6D + aligned metadata."""
    rng = np.random.default_rng(seed)
    a = rng.normal(loc=-2.0, scale=0.2, size=(per_group, 6))
    b = rng.normal(loc=2.0, scale=0.2, size=(per_group, 6))
    X = np.vstack([a, b])
    metadata = pd.DataFrame(
        {
            "player_id": range(len(X)),
            "player_name": [f"p{i}" for i in range(len(X))],
            "team_id": [i % 4 for i in range(len(X))],
            "group": ["a"] * per_group + ["b"] * per_group,
        }
    )
    return X, metadata


def test_auto_grid_size_scales_with_population() -> None:
    small = auto_grid_size(20)
    large = auto_grid_size(400)
    assert small[0] >= 2 and small[1] >= 2
    assert large[0] > small[0]


def test_fit_som_returns_model_and_error() -> None:
    X, _ = _matrix()
    fitted = fit_shot_profile_som(X, grid_size=(4, 4), random_state=42)
    assert fitted.grid_size == (4, 4)
    assert fitted.quantization_error > 0


def test_assign_coordinates_within_grid_and_aligned() -> None:
    X, metadata = _matrix()
    fitted = fit_shot_profile_som(X, grid_size=(5, 4), random_state=42)
    coords = assign_som_coordinates(fitted, X, metadata, kmeans_labels=np.zeros(len(X), int))

    assert len(coords) == len(X)
    assert coords["som_x"].between(0, 4).all()
    assert coords["som_y"].between(0, 3).all()
    assert "kmeans_cluster" in coords.columns
    assert list(coords["player_id"]) == list(metadata["player_id"])


def test_som_separates_distinct_blobs() -> None:
    X, metadata = _matrix()
    fitted = fit_shot_profile_som(X, grid_size=(6, 6), random_state=42)
    coords = assign_som_coordinates(fitted, X, metadata)

    cells_a = set(map(tuple, coords.loc[coords["group"] == "a", ["som_x", "som_y"]].to_numpy()))
    cells_b = set(map(tuple, coords.loc[coords["group"] == "b", ["som_x", "som_y"]].to_numpy()))
    assert cells_a.isdisjoint(cells_b)


def test_som_reproducible_with_fixed_seed() -> None:
    X, metadata = _matrix()
    coords1 = assign_som_coordinates(
        fit_shot_profile_som(X, grid_size=(4, 4), random_state=42), X, metadata
    )
    coords2 = assign_som_coordinates(
        fit_shot_profile_som(X, grid_size=(4, 4), random_state=42), X, metadata
    )
    pd.testing.assert_frame_equal(coords1, coords2)


def test_summarize_som_map_reports_density_and_dominance() -> None:
    X, metadata = _matrix()
    fitted = fit_shot_profile_som(X, grid_size=(4, 4), random_state=42)
    labels = np.array([0] * 12 + [1] * 12)
    coords = assign_som_coordinates(fitted, X, metadata, kmeans_labels=labels)
    summary = summarize_som_map(coords, grid_size=(4, 4))

    assert summary["occupied_cells"] >= 2
    assert summary["total_cells"] == 16
    assert 0 < summary["occupancy"] <= 1
    assert isinstance(summary["dominant_clusters"], pd.DataFrame)
    assert {"som_x", "som_y", "kmeans_cluster", "players"}.issubset(
        summary["dominant_clusters"].columns
    )


def test_small_dataset_handled() -> None:
    rng = np.random.default_rng(1)
    X = rng.normal(size=(4, 6))
    metadata = pd.DataFrame({"player_id": range(4)})
    fitted = fit_shot_profile_som(X, random_state=42)  # auto grid for tiny n
    coords = assign_som_coordinates(fitted, X, metadata)
    assert len(coords) == 4


def test_empty_matrix_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        fit_shot_profile_som(np.empty((0, 6)))
