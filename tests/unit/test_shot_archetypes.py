"""Unit tests for the KMeans shot-archetype model.

Synthetic player-season profiles with three obvious archetypes (rim-heavy,
three-heavy, midrange-heavy); a well-behaved clustering must recover them.
Seeded numpy noise keeps everything deterministic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hoops_lab.models.shot_archetypes import (
    CLUSTER_FEATURES,
    find_closest_players_to_centroids,
    fit_kmeans_shot_archetypes,
    prepare_shot_profile_matrix,
    summarize_kmeans_archetypes,
)

_ARCHETYPES = {
    "rim": {"rim_frequency": 0.7, "midrange_frequency": 0.1, "above_break_three_frequency": 0.1},
    "three": {
        "rim_frequency": 0.15,
        "midrange_frequency": 0.05,
        "above_break_three_frequency": 0.55,
    },
    "mid": {"rim_frequency": 0.2, "midrange_frequency": 0.6, "above_break_three_frequency": 0.1},
}


def _synthetic_profiles(per_group: int = 10, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    pid = 0
    for group, base in _ARCHETYPES.items():
        for _ in range(per_group):
            pid += 1
            noise = rng.normal(0, 0.02, size=3)
            rim = base["rim_frequency"] + noise[0]
            mid = base["midrange_frequency"] + noise[1]
            abt = base["above_break_three_frequency"] + noise[2]
            corner = 0.1
            paint = max(1.0 - rim - mid - abt - corner, 0.0)
            rows.append(
                {
                    "player_id": pid,
                    "player_name": f"{group}-{pid}",
                    "team_id": pid % 3,
                    "team_name": f"Team {pid % 3}",
                    "season": "2025-26",
                    "total_attempts": 400,
                    "group": group,
                    "rim_frequency": rim,
                    "paint_non_rim_frequency": paint,
                    "midrange_frequency": mid,
                    "corner_three_frequency": corner,
                    "above_break_three_frequency": abt,
                    "rim_fg_pct": 0.62,
                    "paint_non_rim_fg_pct": 0.42,
                    "midrange_fg_pct": 0.41,
                    "corner_three_fg_pct": np.nan if pid % 5 == 0 else 0.39,
                    "above_break_three_fg_pct": 0.35,
                    "average_shot_distance": 5 + abt * 25,
                    "points_per_shot": 1.0 + abt,
                    "shot_entropy": 0.5,
                    "zone_diversity": 0.6,
                    "bin_000": 0.5,
                    "bin_001": 0.5,
                }
            )
    return pd.DataFrame(rows)


def test_prepare_matrix_shapes_and_nan_handling() -> None:
    profiles = _synthetic_profiles()
    X, metadata, feature_names, scaler = prepare_shot_profile_matrix(profiles)

    assert X.shape == (len(profiles), len(feature_names))
    assert len(metadata) == len(profiles)
    assert "player_id" in metadata.columns
    assert set(feature_names).issubset(set(CLUSTER_FEATURES))
    assert "bin_000" not in feature_names  # spatial bins stay out of the matrix
    assert not np.isnan(X).any()  # NaN fg_pct imputed
    # Standardized: each column ~zero mean, unit variance.
    assert np.allclose(X.mean(axis=0), 0.0, atol=1e-9)


def test_kmeans_recovers_synthetic_archetypes() -> None:
    profiles = _synthetic_profiles()
    result = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)

    assert len(result.labels) == len(profiles)
    assert result.centroids.shape == (3, len(result.feature_names))
    assert result.inertia > 0
    assert result.silhouette is not None and result.silhouette > 0.4

    # Every synthetic group lands in exactly one cluster.
    assigned = profiles.assign(cluster=result.labels)
    for _, group in assigned.groupby("group"):
        assert group["cluster"].nunique() == 1


def test_kmeans_reproducible_with_fixed_seed() -> None:
    profiles = _synthetic_profiles()
    a = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)
    b = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)
    assert np.array_equal(a.labels, b.labels)
    assert np.allclose(a.centroids.to_numpy(), b.centroids.to_numpy())


def test_centroids_are_in_original_units() -> None:
    profiles = _synthetic_profiles()
    result = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)
    # Frequencies in the de-standardized centroids must look like frequencies.
    assert result.centroids["rim_frequency"].between(0, 1).all()
    assert result.centroids["rim_frequency"].max() > 0.5  # the rim-heavy archetype


def test_summarize_produces_labels_and_drivers() -> None:
    profiles = _synthetic_profiles()
    result = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)
    summary = summarize_kmeans_archetypes(result)

    assert len(summary) == 3
    assert summary["size"].sum() == len(profiles)
    assert (summary["label"].str.len() > 0).all()
    assert summary["label"].nunique() == 3  # labels disambiguated
    for drivers in summary["top_drivers"]:
        assert len(drivers) >= 2
        for driver in drivers:
            assert any(feat in driver for feat in result.feature_names)
    assert (summary["description"].str.len() > 20).all()


def test_closest_players_belong_to_their_cluster() -> None:
    profiles = _synthetic_profiles()
    result = fit_kmeans_shot_archetypes(profiles, n_clusters=3, random_state=42)
    closest = find_closest_players_to_centroids(result, top_k=3)

    assert set(closest["cluster"]) == {0, 1, 2}
    assert len(closest) == 9
    assert (closest.groupby("cluster")["distance"].apply(lambda s: s.is_monotonic_increasing)).all()
    # The player nearest to a centroid is assigned to that cluster.
    for cluster, group in closest.groupby("cluster"):
        top_player = group.iloc[0]["player_id"]
        idx = result.metadata.index[result.metadata["player_id"] == top_player][0]
        assert result.labels[idx] == cluster


def test_too_few_players_raises() -> None:
    profiles = _synthetic_profiles(per_group=1)  # 3 players
    with pytest.raises(ValueError, match="n_clusters"):
        fit_kmeans_shot_archetypes(profiles, n_clusters=6)
