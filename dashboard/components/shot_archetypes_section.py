"""Shot Archetypes section for the Opponent Scouting page.

Renders the unsupervised shot-profile analysis: every shot of the selected
season is aggregated into player-season profile vectors, KMeans extracts
discrete archetypes (centroids = average profiles, not real players) and a
Self-Organizing Map projects the same vectors onto a 2-D similarity grid.
Descriptive analytics only — no prediction, no causality.

Heavy steps (season shot load, profile build, model fits) are cached with
``st.cache_data`` keyed on season + parameters, so reruns with unchanged
controls never refit.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from hoops_lab.features.shot_spatial_features import build_player_season_shot_profile
from hoops_lab.models.shot_archetypes import (
    ShotArchetypeResult,
    find_closest_players_to_centroids,
    fit_kmeans_shot_archetypes,
    summarize_kmeans_archetypes,
)
from hoops_lab.models.shot_som import (
    assign_som_coordinates,
    auto_grid_size,
    fit_shot_profile_som,
    summarize_som_map,
)
from hoops_lab.storage.database import Database
from hoops_lab.visuals.altair_charts import (
    build_centroid_profile_chart,
    build_cluster_distribution_chart,
    build_shot_profile_chart,
    build_som_map_chart,
)
from hoops_lab.visuals.heatmaps import centroid_heatmap
from hoops_lab.visuals.shot_maps import player_shot_map

_BINS = (12, 10)

_PURPOSE = (
    "This section describes **spatial shot archetypes** for the selected season: "
    "it shows which players share similar shot diets, which archetypes emerge "
    "league-wide, and where the scouted team's players sit relative to the league. "
    "It does **not** predict performance and does **not** prove causality."
)

_SOM_EXPLANATION = (
    "KMeans groups players into discrete shot-profile archetypes — each centroid "
    "is the *average profile* of an archetype, not a real player. The SOM instead "
    "projects the same profiles onto a 2-D grid that preserves similarity: players "
    "close on the map have similar shot distributions. Use it to explore continuity, "
    "hybrid profiles and outliers, not to predict performance."
)


@st.cache_data(ttl=3600, show_spinner=False)
def _season_shot_count(_db: Database, season: str) -> int:
    return int(
        _db.query_df("SELECT COUNT(*) AS n FROM shots WHERE season = ?", [season])["n"].iloc[0]
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _player_population(_db: Database, season: str) -> pd.DataFrame:
    """Attempt counts per player (to report min_attempts exclusions cheaply)."""
    return _db.query_df(
        "SELECT PLAYER_ID, COUNT(*) AS attempts FROM shots WHERE season = ? GROUP BY PLAYER_ID",
        [season],
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _season_profiles(_db: Database, season: str, min_attempts: int) -> pd.DataFrame:
    shots = _db.query_df(
        """
        SELECT PLAYER_ID, PLAYER_NAME, TEAM_ID, TEAM_NAME, season,
               SHOT_ZONE_BASIC, SHOT_MADE_FLAG, SHOT_TYPE, SHOT_DISTANCE, LOC_X, LOC_Y
        FROM shots WHERE season = ?
        """,
        [season],
    )
    return build_player_season_shot_profile(shots, min_attempts=min_attempts, bins=_BINS)


@st.cache_data(ttl=3600, show_spinner=False)
def _player_shots(_db: Database, season: str, player_id: int) -> pd.DataFrame:
    return _db.query_df(
        "SELECT LOC_X, LOC_Y, SHOT_MADE_FLAG FROM shots WHERE season = ? AND PLAYER_ID = ?",
        [season, player_id],
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _fit_archetypes(
    _db: Database, season: str, min_attempts: int, n_clusters: int
) -> ShotArchetypeResult:
    profiles = _season_profiles(_db, season, min_attempts)
    return fit_kmeans_shot_archetypes(profiles, n_clusters=n_clusters, random_state=42)


@st.cache_data(ttl=3600, show_spinner=False)
def _fit_som_coords(
    _db: Database,
    season: str,
    min_attempts: int,
    n_clusters: int,
    grid: tuple[int, int],
) -> tuple[pd.DataFrame, float]:
    result = _fit_archetypes(_db, season, min_attempts, n_clusters)
    fitted = fit_shot_profile_som(result.X, grid_size=grid, random_state=42)
    coords = assign_som_coordinates(fitted, result.X, result.metadata, result.labels)
    return coords, fitted.quantization_error


def render_shot_archetypes_section(
    database: Database, team_id: int, team_abbr: str, season: str
) -> None:
    """Render the full Shot Archetypes section.

    Args:
        database: Shared dashboard database handle.
        team_id: Rail-selected (scouted) team.
        team_abbr: Its tricode, for labels.
        season: Rail-selected season — all league shots of this season are used.
    """
    st.header(f"🧬 Shot Archetypes — {season}")
    st.markdown(_PURPOSE)

    if database.table_rows("shots") == 0:
        st.info("No shot data loaded — the archetype analysis needs the shots table.")
        return

    # ---- Controls ------------------------------------------------------------
    controls = st.columns([1.2, 1.2, 1.0, 1.0])
    min_attempts = controls[0].slider(
        "Min attempts (player inclusion)",
        50,
        500,
        100,
        step=25,
        key="arch_min_attempts",
        help="Players below this season attempt count are excluded from the profiles.",
    )
    n_clusters = controls[1].slider(
        "Archetypes (KMeans k)",
        3,
        10,
        6,
        key="arch_n_clusters",
    )
    grid_choice = controls[2].selectbox(
        "SOM grid",
        ["auto", "6 × 6", "8 × 8", "10 × 10"],
        key="arch_som_grid",
    )
    highlight_team = controls[3].toggle(
        f"Highlight {team_abbr}",
        value=True,
        key="arch_highlight_team",
    )

    # ---- Data summary ----------------------------------------------------------
    population = _player_population(database, season)
    included = population.loc[population["attempts"] >= min_attempts]
    excluded = len(population) - len(included)

    if len(included) < 30:
        st.warning(
            f"Only {len(included)} players reach {min_attempts} attempts — the dataset is too "
            "small for stable clustering. Lower the minimum attempts threshold."
        )
        return

    with st.spinner("Building player shot profiles and fitting models..."):
        result = _fit_archetypes(database, season, min_attempts, n_clusters)
        summary = summarize_kmeans_archetypes(result)
        profiles = _season_profiles(database, season, min_attempts)

    total_shots = _season_shot_count(database, season)
    grid = (
        auto_grid_size(len(included))
        if grid_choice == "auto"
        else tuple(int(v) for v in grid_choice.split(" × "))
    )

    meta_cols = st.columns(6)
    meta_cols[0].metric("Season shots", f"{total_shots:,}")
    meta_cols[1].metric("Players included", len(included))
    meta_cols[2].metric("Excluded (low volume)", excluded)
    meta_cols[3].metric("Min attempts", min_attempts)
    meta_cols[4].metric("Archetypes", n_clusters)
    meta_cols[5].metric("SOM grid", f"{grid[0]}×{grid[1]}")

    if excluded > len(population) * 0.6:
        st.caption(
            f"⚠️ Data quality: {excluded}/{len(population)} players fall below the attempt "
            "threshold — archetypes describe rotation players only."
        )

    labels_by_cluster = dict(zip(summary["cluster"], summary["label"], strict=True))
    assigned = result.metadata.assign(
        cluster=result.labels,
        archetype=[labels_by_cluster[c] for c in result.labels],
    )

    # ---- KMeans subsection -----------------------------------------------------
    st.subheader("Discrete archetypes (KMeans)")
    st.caption(
        "Each centroid is the **average profile of its archetype, not a real player**. "
        f"Silhouette score: {result.silhouette:.2f}"
        if result.silhouette is not None
        else "Each centroid is the average profile of its archetype, not a real player."
    )

    dist_col, table_col = st.columns([2, 3])
    with dist_col:
        counts = (
            assigned.groupby("archetype", as_index=False)
            .size()
            .rename(columns={"size": "players"})
            .rename(columns={"archetype": "label"})
        )
        st.altair_chart(build_cluster_distribution_chart(counts), use_container_width=True)
    with table_col:
        st.dataframe(
            summary.assign(top_drivers=summary["top_drivers"].str.join(" · "))[
                ["label", "size", "top_drivers", "description"]
            ],
            hide_index=True,
            use_container_width=True,
        )

    # Centroid z-score profiles (frequencies + shape features only, readable).
    profile_feats = [f for f in result.feature_names if f.endswith("_frequency")] + [
        "average_shot_distance",
        "points_per_shot",
    ]
    long_centroids = (
        result.centroids_scaled[profile_feats]
        .assign(label=[labels_by_cluster[c] for c in range(n_clusters)])
        .melt(id_vars="label", var_name="feature", value_name="value")
    )
    st.altair_chart(build_centroid_profile_chart(long_centroids), use_container_width=True)

    # Per-archetype deep dive: court heatmap + closest real players.
    st.markdown("##### Archetype deep dive")
    pick = st.selectbox("Archetype", summary["label"].tolist(), key="arch_pick")
    pick_cluster = int(summary.loc[summary["label"] == pick, "cluster"].iloc[0])

    heat_col, near_col = st.columns([2, 3])
    with heat_col:
        bin_cols = [c for c in profiles.columns if c.startswith("bin_")]
        member_ids = assigned.loc[assigned["cluster"] == pick_cluster, "player_id"]
        member_bins = profiles.loc[profiles["player_id"].isin(member_ids), bin_cols].mean()
        st.pyplot(
            centroid_heatmap(member_bins.to_numpy(), bins=_BINS, title=pick),
            use_container_width=True,
        )
        st.caption("Average spatial shot frequency of the archetype's members.")
    with near_col:
        closest = find_closest_players_to_centroids(result, top_k=5)
        st.markdown("**Closest real players to each centroid**")
        st.dataframe(
            closest.loc[closest["cluster"] == pick_cluster].drop(columns=["cluster"]),
            hide_index=True,
            use_container_width=True,
            column_config={"distance": st.column_config.NumberColumn(format="%.2f")},
        )

    # Scouted team's players with their archetype.
    st.markdown(f"##### {team_abbr} players by archetype")
    team_rows = assigned.loc[assigned["team_id"] == team_id]
    if team_rows.empty:
        st.info(f"No {team_abbr} player reaches {min_attempts} attempts this season.")
    else:
        st.dataframe(
            team_rows[["player_name", "archetype", "total_attempts"]].sort_values("archetype"),
            hide_index=True,
            use_container_width=True,
        )

    # ---- SOM subsection ----------------------------------------------------------
    st.subheader("Similarity map (Self-Organizing Map)")
    st.markdown(_SOM_EXPLANATION)

    with st.spinner("Training the SOM..."):
        coords, qe = _fit_som_coords(database, season, min_attempts, n_clusters, grid)
    coords = coords.assign(archetype=[labels_by_cluster[c] for c in coords["kmeans_cluster"]])

    player_options = ["(none)"] + sorted(coords["player_name"].tolist())
    selected_player = st.selectbox(
        "Highlight a player",
        player_options,
        key="arch_som_player",
    )
    highlight_player_id = None
    if selected_player != "(none)":
        highlight_player_id = int(
            coords.loc[coords["player_name"] == selected_player, "player_id"].iloc[0]
        )

    som_col, side_col = st.columns([3, 2])
    with som_col:
        st.altair_chart(
            build_som_map_chart(
                coords,
                grid_size=grid,
                highlight_team_id=team_id if highlight_team else None,
                highlight_player_id=highlight_player_id,
            ),
            use_container_width=True,
        )
    with side_col:
        som_summary = summarize_som_map(coords, grid_size=grid)
        st.metric("Occupied cells", f"{som_summary['occupied_cells']}/{som_summary['total_cells']}")
        st.metric("Quantization error", f"{qe:.2f}")
        if highlight_player_id is not None:
            row = coords.loc[coords["player_id"] == highlight_player_id].iloc[0]
            st.markdown(
                f"**{row['player_name']}** — cell ({row['som_x']}, {row['som_y']}), "
                f"archetype *{row['archetype']}*, {row['total_attempts']} attempts."
            )
            shots = _player_shots(database, season, highlight_player_id)
            st.pyplot(
                player_shot_map(shots, title=str(row["player_name"])),
                use_container_width=True,
            )
        else:
            st.caption(
                "Sparse cells host atypical profiles (outliers); regions dominated by one "
                "color are stable archetype zones; color changes across neighboring cells "
                "show smooth transitions between shot diets."
            )

    # Zone profile of the selected player vs nobody — quick Altair block reuse.
    if highlight_player_id is not None:
        prof = profiles.loc[profiles["player_id"] == highlight_player_id]
        if not prof.empty:
            row = prof.iloc[0]
            zone_data = pd.DataFrame(
                {
                    "zone": ["RIM", "PAINT", "MID", "CORNER 3", "ABOVE BREAK 3"],
                    "frequency": [
                        row["rim_frequency"],
                        row["paint_non_rim_frequency"],
                        row["midrange_frequency"],
                        row["corner_three_frequency"],
                        row["above_break_three_frequency"],
                    ],
                    "fg_pct": [
                        row["rim_fg_pct"],
                        row["paint_non_rim_fg_pct"],
                        row["midrange_fg_pct"],
                        row["corner_three_fg_pct"],
                        row["above_break_three_fg_pct"],
                    ],
                }
            )
            st.altair_chart(
                build_shot_profile_chart(zone_data, title=f"{selected_player} — zone profile"),
                use_container_width=True,
            )
