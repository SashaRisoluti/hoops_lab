"""Self-Organizing Map over the same shot-profile vectors used by KMeans.

The SOM does not replace KMeans: it projects the standardized profiles onto
a 2-D grid preserving similarity, so nearby players have similar shot
distributions. It is a complementary, topology-preserving view — useful to
spot hybrid profiles, transitions between archetypes and outliers, not to
predict performance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from minisom import MiniSom


@dataclass(frozen=True)
class FittedSom:
    """A trained SOM plus the settings needed to reuse it."""

    som: MiniSom
    grid_size: tuple[int, int]
    quantization_error: float


def auto_grid_size(n_samples: int) -> tuple[int, int]:
    """Square grid from the 5*sqrt(N) rule of thumb (minimum 2x2)."""
    side = max(2, math.ceil(math.sqrt(5 * math.sqrt(max(n_samples, 1)))))
    return side, side


def fit_shot_profile_som(
    X: np.ndarray,
    grid_size: tuple[int, int] | None = None,
    random_state: int = 42,
    num_iterations: int = 2000,
) -> FittedSom:
    """Train a SOM on the standardized profile matrix.

    Args:
        X: Standardized matrix (same one KMeans is fitted on).
        grid_size: (width, height) of the map; defaults to
            :func:`auto_grid_size` of the sample count.
        random_state: Fixed seed — output is reproducible.
        num_iterations: Training iterations (random sampling).

    Returns:
        A :class:`FittedSom` with the trained map and its quantization error.

    Raises:
        ValueError: If ``X`` is empty.
    """
    if X.size == 0:
        raise ValueError("X is empty — nothing to map")
    width, height = grid_size or auto_grid_size(len(X))
    sigma = max(min(width, height) / 2.0 - 0.5, 0.5)

    som = MiniSom(
        width,
        height,
        X.shape[1],
        sigma=sigma,
        learning_rate=0.5,
        random_seed=random_state,
    )
    som.pca_weights_init(X) if len(X) > X.shape[1] else som.random_weights_init(X)
    som.train(X, num_iterations, random_order=True)
    return FittedSom(
        som=som,
        grid_size=(width, height),
        quantization_error=float(som.quantization_error(X)),
    )


def assign_som_coordinates(
    fitted: FittedSom,
    X: np.ndarray,
    metadata: pd.DataFrame,
    kmeans_labels: np.ndarray | None = None,
) -> pd.DataFrame:
    """Map every profile to its best-matching SOM cell.

    Args:
        fitted: A trained :class:`FittedSom`.
        X: The matrix the SOM was trained on (row-aligned with metadata).
        metadata: Player metadata, one row per X row.
        kmeans_labels: Optional KMeans labels to overlay on the map.

    Returns:
        ``metadata`` copy with ``som_x``/``som_y`` (grid cell) and, when
        provided, ``kmeans_cluster`` columns appended.
    """
    coords = metadata.reset_index(drop=True).copy()
    winners = [fitted.som.winner(row) for row in X]
    coords["som_x"] = [w[0] for w in winners]
    coords["som_y"] = [w[1] for w in winners]
    if kmeans_labels is not None:
        coords["kmeans_cluster"] = kmeans_labels
    return coords


def summarize_som_map(coords: pd.DataFrame, grid_size: tuple[int, int]) -> dict:
    """Readable synthesis of the trained map.

    Args:
        coords: Output of :func:`assign_som_coordinates`.
        grid_size: (width, height) of the map.

    Returns:
        Dict with ``occupied_cells``, ``total_cells``, ``occupancy``,
        ``max_cell_players`` and ``dominant_clusters`` (per occupied cell:
        player count and, when available, the dominant KMeans cluster) —
        sparse cells point at outliers, dominated regions at archetype zones.
    """
    total_cells = grid_size[0] * grid_size[1]
    per_cell = coords.groupby(["som_x", "som_y"], as_index=False).agg(
        players=("som_x", "size"),
        **(
            {"kmeans_cluster": ("kmeans_cluster", lambda s: int(s.mode().iloc[0]))}
            if "kmeans_cluster" in coords.columns
            else {}
        ),
    )
    if "kmeans_cluster" not in per_cell.columns:
        per_cell["kmeans_cluster"] = pd.NA
    return {
        "occupied_cells": int(len(per_cell)),
        "total_cells": int(total_cells),
        "occupancy": float(len(per_cell) / total_cells),
        "max_cell_players": int(per_cell["players"].max()),
        "dominant_clusters": per_cell,
    }
