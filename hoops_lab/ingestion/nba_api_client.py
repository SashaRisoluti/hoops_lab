"""Thin, rate-limited wrapper around ``nba_api`` (stats.nba.com).

ALL remote calls in the project go through :class:`NBAApiClient`, which
enforces a minimum delay between consecutive requests, applies a timeout and
retries failed calls with logging. Never instantiate nba_api endpoints
directly elsewhere.

Run as a module for a connectivity smoke test (downloads league-wide player
stats for the 2023-24 season and saves them as Parquet)::

    python -m hoops_lab.ingestion.nba_api_client
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats
from nba_api.stats.static import teams as static_teams

from hoops_lab.config import NBA_API_DELAY, NBA_API_TIMEOUT, REFERENCE_TEAM

logger = logging.getLogger(__name__)

#: Where raw downloads are stored, relative to the repo root (run from there).
RAW_DATA_DIR = Path("data/raw")


class NBAApiClient:
    """Rate-limited client for stats.nba.com via the ``nba_api`` package.

    Parameters
    ----------
    delay:
        Minimum seconds between consecutive API calls (default: ``NBA_API_DELAY``).
    timeout:
        Per-request timeout in seconds (default: ``NBA_API_TIMEOUT``).
    max_retries:
        How many times a failing call is attempted before raising.
    """

    def __init__(
        self,
        delay: float = NBA_API_DELAY,
        timeout: int = NBA_API_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_call = 0.0

    def _throttle(self) -> None:
        """Sleep so that consecutive calls are at least ``self.delay`` seconds apart."""
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_call = time.monotonic()

    def _call(self, endpoint_cls: type, **params: Any) -> Any:
        """Instantiate an nba_api endpoint with throttling, timeout and retries.

        Parameters
        ----------
        endpoint_cls:
            An endpoint class from ``nba_api.stats.endpoints``.
        **params:
            Keyword arguments forwarded to the endpoint constructor.

        Returns
        -------
        The instantiated endpoint (the request is performed by nba_api on
        construction).

        Raises
        ------
        ConnectionError
            If the call still fails after ``max_retries`` attempts.
        """
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                return endpoint_cls(timeout=self.timeout, **params)
            except Exception as exc:  # nba_api surfaces requests exceptions
                last_error = exc
                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    endpoint_cls.__name__,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(attempt * 1.5)  # simple linear backoff
        raise ConnectionError(
            f"{endpoint_cls.__name__} failed after {self.max_retries} attempts"
        ) from last_error

    @staticmethod
    def team_id_from_name(full_name: str) -> int:
        """Resolve an NBA team id from its full name (offline, static data).

        Parameters
        ----------
        full_name:
            Team name as it appears on stats.nba.com, e.g. ``"Dallas Mavericks"``.
            This is how ``REFERENCE_TEAM`` is resolved — swapping the reference
            team requires no code change.

        Returns
        -------
        The official NBA team id (e.g. ``1610612742`` for Dallas).

        Raises
        ------
        ValueError
            If no team matches ``full_name``.
        """
        matches = static_teams.find_teams_by_full_name(full_name)
        if not matches:
            raise ValueError(f"No NBA team matches {full_name!r}")
        return int(matches[0]["id"])

    def league_player_stats(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        per_mode: str = "PerGame",
    ) -> pd.DataFrame:
        """Download league-wide per-player stats for a season.

        Parameters
        ----------
        season:
            Season string in NBA format, e.g. ``"2023-24"``.
        season_type:
            ``"Regular Season"``, ``"Playoffs"`` or ``"Pre Season"``.
        per_mode:
            ``"PerGame"``, ``"Totals"`` or ``"Per100Possessions"``.

        Returns
        -------
        One row per player with base box-score stats (GP, MIN, PTS, REB, AST, ...).
        """
        endpoint = self._call(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star=season_type,
            per_mode_detailed=per_mode,
        )
        df = endpoint.get_data_frames()[0]
        logger.info("LeagueDashPlayerStats %s: %d rows x %d cols", season, *df.shape)
        return df

    def check_connection(self, season: str = "2023-24") -> bool:
        """Return True if stats.nba.com is reachable and returns data."""
        try:
            return not self.league_player_stats(season=season).empty
        except Exception as exc:
            logger.error("Connection check failed: %s", exc)
            return False


def run_smoke_test(season: str = "2023-24", save: bool = True) -> pd.DataFrame:
    """Connectivity smoke test: download player stats, print a summary, save Parquet.

    Parameters
    ----------
    season:
        Season to download (default ``"2023-24"`` as per the build plan).
    save:
        When True, store the raw data as ``data/raw/player_stats_<season>.parquet``.

    Returns
    -------
    The downloaded league-wide player stats DataFrame.
    """
    client = NBAApiClient()

    ref_team_id = NBAApiClient.team_id_from_name(REFERENCE_TEAM)
    print(
        f"Reference team: {REFERENCE_TEAM} (id {ref_team_id}) "
        "— set REFERENCE_TEAM in .env to change it"
    )

    df = client.league_player_stats(season=season)
    print(f"OK — downloaded {len(df)} player rows for {season}")

    top = df.nlargest(5, "PTS")[["PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "PTS"]]
    print(f"Top 5 scorers (PPG, {season}):")
    print(top.to_string(index=False))

    if save:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = RAW_DATA_DIR / f"player_stats_{season}.parquet"
        df.to_parquet(out, index=False)
        print(f"Saved raw data to {out}")
    return df


if __name__ == "__main__":
    import sys

    # Windows consoles may default to cp1252, which cannot print players like
    # Luka Dončić — force UTF-8 for the smoke-test output.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_smoke_test()
