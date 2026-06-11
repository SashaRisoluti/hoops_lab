"""Historical data downloads from stats.nba.com, saved as raw Parquet.

League-wide datasets are downloaded with a single endpoint call per season;
shot charts and play-by-play are downloaded for the reference team and a
sample of its games, per the public-demo data strategy (README).

Run as a module to download the full demo bundle (DEMO_SEASONS by default;
use ``scripts/extend_seasons.py`` to add league-wide extras for a season)::

    python -m hoops_lab.ingestion.historical
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import (
    leaguedashlineups,
    leaguedashplayerstats,
    leaguedashteamstats,
    leaguegamelog,
    playbyplayv3,
    shotchartdetail,
)
from nba_api.stats.static import teams as static_teams

from hoops_lab.config import DEMO_SEASONS, REFERENCE_TEAM
from hoops_lab.ingestion.nba_api_client import RAW_DATA_DIR, NBAApiClient
from hoops_lab.ingestion.schemas import DownloadResult, HistoricalDownloadRequest, SeasonType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetSpec:
    """A league-level dataset: endpoint class plus fixed extra parameters."""

    endpoint: type
    extra_params: dict[str, Any] = field(default_factory=dict)


#: League-wide datasets downloadable with one endpoint call per season.
LEAGUE_DATASETS: dict[str, DatasetSpec] = {
    "player_box": DatasetSpec(leaguegamelog.LeagueGameLog, {"player_or_team_abbreviation": "P"}),
    "team_box": DatasetSpec(leaguegamelog.LeagueGameLog, {"player_or_team_abbreviation": "T"}),
    "player_stats": DatasetSpec(
        leaguedashplayerstats.LeagueDashPlayerStats,
        {"per_mode_detailed": "PerGame", "measure_type_detailed_defense": "Base"},
    ),
    "player_advanced": DatasetSpec(
        leaguedashplayerstats.LeagueDashPlayerStats,
        {"per_mode_detailed": "PerGame", "measure_type_detailed_defense": "Advanced"},
    ),
    "team_stats": DatasetSpec(
        leaguedashteamstats.LeagueDashTeamStats,
        {"per_mode_detailed": "PerGame", "measure_type_detailed_defense": "Base"},
    ),
    "team_advanced": DatasetSpec(
        leaguedashteamstats.LeagueDashTeamStats,
        {"per_mode_detailed": "PerGame", "measure_type_detailed_defense": "Advanced"},
    ),
}
# NOTE: lineups are intentionally NOT a league dataset — the league-wide
# LeagueDashLineups response is capped at 2000 rows server-side, so they are
# downloaded with one query per team (see HistoricalDownloader.download_lineups).


def recent_team_game_ids(team_box: pd.DataFrame, team_id: int, n: int) -> list[str]:
    """Return the most recent GAME_IDs for one team from a team_box DataFrame.

    Parameters
    ----------
    team_box:
        Team game log as returned by the ``team_box`` dataset (LeagueGameLog).
    team_id:
        Official NBA team id (see ``NBAApiClient.team_id_from_name``).
    n:
        Maximum number of game ids to return.

    Returns
    -------
    GAME_IDs sorted from most recent to oldest.
    """
    games = team_box.loc[team_box["TEAM_ID"] == team_id]
    games = games.sort_values("GAME_DATE", ascending=False)
    return games["GAME_ID"].head(n).astype(str).tolist()


def sample_game_ids_per_team(team_box: pd.DataFrame, per_team: int) -> list[str]:
    """Union of every team's most recent ``per_team`` GAME_IDs (sorted).

    Shared games (each game involves two teams) appear once — the cheap way
    to build a league-wide play-by-play sample with guaranteed per-team
    coverage.
    """
    ids: set[str] = set()
    for team_id in team_box["TEAM_ID"].unique():
        ids.update(recent_team_game_ids(team_box, int(team_id), per_team))
    return sorted(ids)


class HistoricalDownloader:
    """Downloads historical NBA data and stores it as Parquet in ``raw_dir``.

    All network access goes through the injected :class:`NBAApiClient`
    (rate limiting, timeout and retries live there).

    Parameters
    ----------
    client:
        The API client to use; a default-configured one is created if omitted.
    raw_dir:
        Destination directory for raw Parquet files.
    """

    def __init__(
        self,
        client: NBAApiClient | None = None,
        raw_dir: Path | str = RAW_DATA_DIR,
    ) -> None:
        self.client = client or NBAApiClient()
        self.raw_dir = Path(raw_dir)

    def _save(self, df: pd.DataFrame, dataset: str, season: str) -> DownloadResult:
        """Write ``df`` to ``raw_dir/<dataset>_<season>.parquet`` and report it."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        path = self.raw_dir / f"{dataset}_{season}.parquet"
        df.to_parquet(path, index=False)
        result = DownloadResult(dataset=dataset, season=season, rows=len(df), path=path)
        logger.info("%s %s: %d rows -> %s", dataset, season, result.rows, path)
        return result

    def download_dataset(
        self,
        dataset: str,
        season: str,
        season_type: SeasonType = "Regular Season",
    ) -> DownloadResult:
        """Download one league-level dataset for one season and save it.

        Parameters
        ----------
        dataset:
            A key of :data:`LEAGUE_DATASETS`.
        season:
            Season in NBA format, e.g. ``"2023-24"``.
        season_type:
            Season segment to download.

        Raises
        ------
        KeyError
            If ``dataset`` is not a known league dataset.
        """
        if dataset not in LEAGUE_DATASETS:
            raise KeyError(f"{dataset!r} is not a league dataset; known: {sorted(LEAGUE_DATASETS)}")
        spec = LEAGUE_DATASETS[dataset]
        df = self.client.fetch_df(
            spec.endpoint,
            season=season,
            season_type_all_star=season_type,
            **spec.extra_params,
        )
        return self._save(df, dataset, season)

    def download_season_bundle(
        self,
        season: str,
        season_type: SeasonType = "Regular Season",
    ) -> list[DownloadResult]:
        """Download every league-level dataset for one season."""
        return [self.download_dataset(name, season, season_type) for name in LEAGUE_DATASETS]

    def download_lineups(
        self,
        season: str,
        season_type: SeasonType = "Regular Season",
    ) -> DownloadResult:
        """Download 5-man lineup stats with one query per NBA team.

        The league-wide LeagueDashLineups endpoint caps its response at 2000
        rows; querying team by team (30 throttled calls per season) returns
        the complete lineup population instead.
        """
        frames = [
            self.client.fetch_df(
                leaguedashlineups.LeagueDashLineups,
                season=season,
                season_type_all_star=season_type,
                team_id_nullable=team["id"],
                group_quantity=5,
                per_mode_detailed="Totals",
                measure_type_detailed_defense="Base",
            )
            for team in static_teams.get_teams()
        ]
        df = pd.concat(frames, ignore_index=True)
        return self._save(df, "lineups", season)

    def download_shot_chart(
        self,
        season: str,
        team_id: int,
        player_id: int = 0,
        season_type: SeasonType = "Regular Season",
    ) -> DownloadResult:
        """Download all shot attempts (FGA) for one team (and optionally player).

        Per the demo data strategy, shots are downloaded for the reference team
        only; pass ``player_id`` to narrow down to a single player.
        """
        df = self.client.fetch_df(
            shotchartdetail.ShotChartDetail,
            team_id=team_id,
            player_id=player_id,
            season_nullable=season,
            season_type_all_star=season_type,
            context_measure_simple="FGA",
        )
        # Team id in the name so every team's file coexists in data/raw.
        return self._save(df, f"shot_chart_{team_id}", season)

    def download_league_shot_charts(
        self,
        season: str,
        season_type: SeasonType = "Regular Season",
    ) -> list[DownloadResult]:
        """Download every team's shot chart for one season (30 throttled calls)."""
        return [
            self.download_shot_chart(season, team_id=team["id"], season_type=season_type)
            for team in static_teams.get_teams()
        ]

    def download_play_by_play(self, game_ids: list[str], season: str) -> DownloadResult:
        """Download play-by-play for a sample of games, merged into one file.

        Parameters
        ----------
        game_ids:
            GAME_IDs to download (see :func:`recent_team_game_ids`).
        season:
            Season label used for the output file name.
        """
        frames = [
            self.client.fetch_df(playbyplayv3.PlayByPlayV3, game_id=game_id) for game_id in game_ids
        ]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return self._save(df, "play_by_play_sample", season)


def run_demo_download(
    seasons: list[str] | None = None,
    pbp_games_per_season: int = 8,
) -> list[DownloadResult]:
    """Download the full public-demo bundle.

    For each season: all league-level datasets, the reference team's shot
    chart, and play-by-play for the team's ``pbp_games_per_season`` most
    recent games.
    """
    request = HistoricalDownloadRequest(seasons=seasons or DEMO_SEASONS)
    downloader = HistoricalDownloader()
    team_id = NBAApiClient.team_id_from_name(REFERENCE_TEAM)

    results: list[DownloadResult] = []
    for season in request.seasons:
        bundle = downloader.download_season_bundle(season, request.season_type)
        results.extend(bundle)
        results.append(downloader.download_lineups(season, request.season_type))
        results.append(downloader.download_shot_chart(season, team_id=team_id))

        team_box = next(r for r in bundle if r.dataset == "team_box")
        game_ids = recent_team_game_ids(
            pd.read_parquet(team_box.path), team_id, pbp_games_per_season
        )
        results.append(downloader.download_play_by_play(game_ids, season))
        print(f"{season}: {sum(r.rows for r in results):,} cumulative rows")

    print(f"Done — {len(results)} datasets in {downloader.raw_dir}")
    return results


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_demo_download()
