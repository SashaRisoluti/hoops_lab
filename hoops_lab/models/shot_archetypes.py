"""KMeans shot archetypes over player-season shot-profile vectors.

The unit of clustering is the player-season profile produced by
``hoops_lab.features.shot_spatial_features`` — never the raw shots. Each
centroid is the average profile of an archetype (not a real player); the
summary translates centroids into readable labels and feature drivers, and
``find_closest_players_to_centroids`` grounds every archetype with real
example players.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

#: Interpretable features used for clustering. Spatial ``bin_###`` frequencies
#: stay OUT of the matrix (120 noisy dimensions would dominate the distance);
#: they are still used downstream to draw cluster heatmaps from member means.
CLUSTER_FEATURES: list[str] = [
    "rim_frequency",
    "paint_non_rim_frequency",
    "midrange_frequency",
    "corner_three_frequency",
    "above_break_three_frequency",
    "rim_fg_pct",
    "paint_non_rim_fg_pct",
    "midrange_fg_pct",
    "corner_three_fg_pct",
    "above_break_three_fg_pct",
    "average_shot_distance",
    "points_per_shot",
    "shot_entropy",
    "zone_diversity",
]

#: (feature, direction) -> human label for the dominant centroid driver.
_DRIVER_LABELS: dict[tuple[str, int], str] = {
    ("rim_frequency", 1): "Rim Pressure",
    ("rim_frequency", -1): "Low Rim Pressure",
    ("paint_non_rim_frequency", 1): "Paint-Oriented Interior",
    ("midrange_frequency", 1): "Midrange Heavy",
    ("corner_three_frequency", 1): "Corner Three Heavy",
    ("above_break_three_frequency", 1): "Above-the-Break Volume",
    ("average_shot_distance", 1): "Perimeter-Heavy",
    ("average_shot_distance", -1): "Interior-Bound",
    ("points_per_shot", 1): "High-Value Shot Diet",
    ("shot_entropy", 1): "Balanced Modern Spacing",
    ("zone_diversity", 1): "Balanced Modern Spacing",
}


@dataclass(frozen=True)
class ShotArchetypeResult:
    """Everything a UI needs from a fitted archetype model."""

    model: KMeans
    labels: np.ndarray
    centroids: pd.DataFrame  # original units (de-standardized)
    centroids_scaled: pd.DataFrame  # z-scores vs the league mean
    inertia: float
    silhouette: float | None
    metadata: pd.DataFrame  # one row per clustered player, original index reset
    feature_names: list[str]
    scaler: StandardScaler
    X: np.ndarray  # the standardized matrix the model was fitted on


def prepare_shot_profile_matrix(
    profiles: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> tuple[np.ndarray, pd.DataFrame, list[str], StandardScaler]:
    """Profiles DataFrame -> standardized matrix + aligned metadata.

    Args:
        profiles: Player-season (or team-season) profile rows.
        feature_cols: Numeric features to use; defaults to the subset of
            ``CLUSTER_FEATURES`` present in the frame.

    Returns:
        ``(X, metadata, feature_names, scaler)`` where X is standardized,
        NaNs (e.g. FG% of an unused zone) are imputed with the column mean,
        and ``metadata`` carries the non-feature columns row-aligned with X.

    Raises:
        ValueError: If the frame is empty or no usable feature is found.
    """
    if profiles.empty:
        raise ValueError("profiles frame is empty — nothing to cluster")
    feature_names = [c for c in (feature_cols or CLUSTER_FEATURES) if c in profiles.columns]
    if not feature_names:
        raise ValueError("no clustering features found in the profiles frame")

    features = profiles[feature_names].astype(float)
    features = features.fillna(features.mean())
    scaler = StandardScaler()
    X = scaler.fit_transform(features.to_numpy())

    metadata = profiles.drop(columns=feature_names).reset_index(drop=True)
    return X, metadata, feature_names, scaler


def fit_kmeans_shot_archetypes(
    profiles: pd.DataFrame,
    n_clusters: int = 6,
    random_state: int = 42,
    feature_cols: list[str] | None = None,
) -> ShotArchetypeResult:
    """Fit KMeans on player-season shot profiles.

    Args:
        profiles: Output of ``build_player_season_shot_profile``.
        n_clusters: Number of archetypes (UI-configurable).
        random_state: Fixed seed — results are reproducible.
        feature_cols: Optional feature override (see
            :func:`prepare_shot_profile_matrix`).

    Returns:
        A :class:`ShotArchetypeResult` with labels, centroids in original
        units and z-scores, inertia and silhouette score.

    Raises:
        ValueError: If there are fewer profiles than ``n_clusters``.
    """
    X, metadata, feature_names, scaler = prepare_shot_profile_matrix(profiles, feature_cols)
    if len(X) < n_clusters:
        raise ValueError(f"{len(X)} profiles cannot support n_clusters={n_clusters}")

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(X)

    silhouette = None
    if n_clusters >= 2 and len(X) > n_clusters:
        silhouette = float(silhouette_score(X, labels))

    centroids_scaled = pd.DataFrame(model.cluster_centers_, columns=feature_names)
    centroids = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=feature_names
    )
    return ShotArchetypeResult(
        model=model,
        labels=labels,
        centroids=centroids,
        centroids_scaled=centroids_scaled,
        inertia=float(model.inertia_),
        silhouette=silhouette,
        metadata=metadata,
        feature_names=feature_names,
        scaler=scaler,
        X=X,
    )


def _archetype_label(z_scores: pd.Series) -> str:
    """Readable name from the strongest centroid z-score."""
    strongest = z_scores.abs().sort_values(ascending=False)
    if strongest.iloc[0] < 0.5:
        return "Balanced Modern Spacing"
    feature = str(strongest.index[0])
    direction = 1 if z_scores[feature] > 0 else -1
    fallback = f"{'High' if direction > 0 else 'Low'} {feature.replace('_', ' ')}"
    return _DRIVER_LABELS.get((feature, direction), fallback)


def summarize_kmeans_archetypes(
    result: ShotArchetypeResult, top_n_drivers: int = 3
) -> pd.DataFrame:
    """Centroids -> one readable row per archetype.

    Args:
        result: A fitted :class:`ShotArchetypeResult`.
        top_n_drivers: How many feature drivers to report per cluster.

    Returns:
        DataFrame with cluster, label (deduplicated), size, top_drivers
        (list of "feature ↑/↓ (value)" strings) and a description sentence.
    """
    rows = []
    for cluster in range(len(result.centroids)):
        z = result.centroids_scaled.iloc[cluster]
        raw = result.centroids.iloc[cluster]
        drivers_idx = z.abs().sort_values(ascending=False).index[:top_n_drivers]
        drivers = [
            f"{feat} {'↑' if z[feat] > 0 else '↓'} ({raw[feat]:.2f})" for feat in drivers_idx
        ]
        phrases = [
            f"{'above' if z[feat] > 0 else 'below'}-average {feat.replace('_', ' ')}"
            f" ({raw[feat]:.2f})"
            for feat in drivers_idx
        ]
        rows.append(
            {
                "cluster": cluster,
                "label": _archetype_label(z),
                "size": int((result.labels == cluster).sum()),
                "top_drivers": drivers,
                "description": (
                    "Average profile of this archetype (not a real player): "
                    + ", ".join(phrases)
                    + "."
                ),
            }
        )
    summary = pd.DataFrame(rows)

    # Disambiguate duplicate labels with the next strongest driver.
    counts = summary["label"].value_counts()
    for label in counts[counts > 1].index:
        for offset, idx in enumerate(summary.index[summary["label"] == label]):
            if offset:
                second = summary.loc[idx, "top_drivers"][1].split(" ")[0].replace("_", " ")
                summary.loc[idx, "label"] = f"{label} — {second}"
    return summary


def find_closest_players_to_centroids(result: ShotArchetypeResult, top_k: int = 3) -> pd.DataFrame:
    """Real example players nearest to each centroid (in standardized space).

    Args:
        result: A fitted :class:`ShotArchetypeResult`.
        top_k: Players per centroid.

    Returns:
        DataFrame with cluster, rank (1 = closest), player metadata columns
        and the euclidean distance to the centroid.
    """
    rows = []
    meta_cols = [
        c
        for c in ("player_id", "player_name", "team_id", "team_name", "total_attempts")
        if c in result.metadata.columns
    ]
    for cluster in range(len(result.centroids)):
        center = result.model.cluster_centers_[cluster]
        distances = np.linalg.norm(result.X - center, axis=1)
        for rank, idx in enumerate(np.argsort(distances)[:top_k], start=1):
            rows.append(
                {"cluster": cluster, "rank": rank}
                | result.metadata.iloc[idx][meta_cols].to_dict()
                | {"distance": float(distances[idx])}
            )
    return pd.DataFrame(rows)
