"""Throttled polling of the live feed, with a stats.nba.com fallback.

The page polls on a timer (``st.fragment(run_every=...)``); this class
guarantees a minimum interval between consecutive remote calls to the same
feed regardless of how often the UI asks. Each feed (the scoreboard, and every
game's play-by-play) runs on its own clock: a shared clock let the scoreboard
call, made first on every rerun, starve the play-by-play forever.

Every fetch tries the live CDN first and falls back to the stats endpoints when
it fails, and events always come back in the stats-format contract, so the page
does not care which source answered.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import pandas as pd

from hoops_lab.config import NBA_API_DELAY
from hoops_lab.features.possession import sort_chronological
from hoops_lab.ingestion.live import (
    LIVE_TIMEOUT,
    adapt_live_actions,
    fetch_live_play_by_play,
    fetch_live_scoreboard,
    fetch_stats_play_by_play,
    fetch_stats_scoreboard,
    nba_today,
)
from hoops_lab.ingestion.nba_api_client import NBAApiClient

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Display names of the two sources, as stored in ``LivePoller.source``.
LIVE_FEED = "NBA live feed"
STATS_FALLBACK = "stats.nba.com fallback"


class LivePoller:
    """Rate-limited scoreboard and play-by-play, live CDN first, stats.nba.com fallback.

    Args:
        min_interval: Minimum seconds between two remote calls to the same feed.
        client: Client for the stats fallback; defaults to a short-timeout,
            single-attempt one so a blocked stats.nba.com cannot hang the page.
    """

    def __init__(
        self,
        min_interval: float = max(2.0, NBA_API_DELAY),
        client: NBAApiClient | None = None,
    ) -> None:
        self.min_interval = min_interval
        self.client = client or NBAApiClient(timeout=LIVE_TIMEOUT, max_retries=1)
        #: Source of the last successful remote fetch (``LIVE_FEED`` / ``STATS_FALLBACK``).
        self.source: str | None = None
        #: When that fetch happened, US Eastern (the scoreboard's own time zone).
        self.updated_at: pd.Timestamp | None = None
        self._cache: dict[str, object] = {}
        self._fetched_at: dict[str, float] = {}

    def _get(self, key: str, fetch: Callable[[], T]) -> T:
        """Cached value for ``key``, refetched once ``min_interval`` has passed."""
        now = time.monotonic()
        if key not in self._cache or now - self._fetched_at[key] >= self.min_interval:
            self._cache[key] = fetch()
            self._fetched_at[key] = now
        return self._cache[key]

    def _fetch(self, live: Callable[[], T], stats: Callable[[], T]) -> T:
        """Live CDN first, stats.nba.com when it fails; records which one answered."""
        try:
            result, source = live(), LIVE_FEED
        except Exception as live_exc:
            logger.warning("live feed failed, trying stats.nba.com: %r", live_exc)
            try:
                result, source = stats(), STATS_FALLBACK
            except Exception as stats_exc:
                logger.warning("stats.nba.com fallback failed: %r", stats_exc)
                raise ConnectionError(
                    "NBA live feed and stats.nba.com fallback both unavailable"
                ) from stats_exc
        self.source, self.updated_at = source, pd.Timestamp.now(tz="America/New_York")
        return result

    def scoreboard(self) -> list[dict]:
        """Tonight's games (cached within the polling interval)."""
        return self._get(
            "scoreboard",
            lambda: self._fetch(
                fetch_live_scoreboard, lambda: fetch_stats_scoreboard(self.client, nba_today())
            ),
        )

    def events(self, game_id: str) -> pd.DataFrame:
        """One game's events so far in the stats-format contract, chronological.

        Live-feed actions go through ``adapt_live_actions``; PBPv3 is used as-is.
        """

        def fetch() -> pd.DataFrame:
            frame = self._fetch(
                lambda: adapt_live_actions(fetch_live_play_by_play(game_id), game_id=game_id),
                lambda: fetch_stats_play_by_play(self.client, game_id),
            )
            return sort_chronological(frame) if len(frame) else frame

        return self._get(f"pbp:{game_id}", fetch)
