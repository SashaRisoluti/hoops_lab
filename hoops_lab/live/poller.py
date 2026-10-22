"""Throttled polling of nba_api live endpoints.

In the Streamlit MVP the "poll" is triggered by user refresh / autorefresh;
this class guarantees a minimum interval between consecutive remote calls to
the same feed regardless of how often the UI asks. Each feed (the scoreboard,
and every game's play-by-play) runs on its own clock: a shared clock let the
scoreboard call, made first on every rerun, starve the play-by-play forever.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from hoops_lab.config import NBA_API_DELAY
from hoops_lab.ingestion.live import fetch_live_play_by_play, fetch_live_scoreboard


class LivePoller:
    """Rate-limited access to the live scoreboard and play-by-play."""

    def __init__(self, min_interval: float = max(2.0, NBA_API_DELAY)) -> None:
        self.min_interval = min_interval
        self._cache: dict[str, list[dict]] = {}
        self._fetched_at: dict[str, float] = {}

    def _get(self, key: str, fetch: Callable[[], list[dict]]) -> list[dict]:
        """Cached value for ``key``, refetched once ``min_interval`` has passed."""
        now = time.monotonic()
        if key not in self._cache or now - self._fetched_at[key] >= self.min_interval:
            self._cache[key] = fetch()
            self._fetched_at[key] = now
        return self._cache[key]

    def scoreboard(self) -> list[dict]:
        """Today's games (cached within the polling interval)."""
        return self._get("scoreboard", fetch_live_scoreboard)

    def play_by_play(self, game_id: str) -> list[dict]:
        """Actions so far for one game (cached within the polling interval)."""
        return self._get(f"pbp:{game_id}", lambda: fetch_live_play_by_play(game_id))
