"""Throttled polling of nba_api live endpoints.

In the Streamlit MVP the "poll" is triggered by user refresh / autorefresh;
this class guarantees a minimum interval between consecutive remote calls
regardless of how often the UI asks.
"""

from __future__ import annotations

import time

from hoops_lab.config import NBA_API_DELAY
from hoops_lab.ingestion.live import fetch_live_play_by_play, fetch_live_scoreboard


class LivePoller:
    """Rate-limited access to the live scoreboard and play-by-play."""

    def __init__(self, min_interval: float = max(2.0, NBA_API_DELAY)) -> None:
        self.min_interval = min_interval
        self._last_call = 0.0
        self._scoreboard_cache: list[dict] = []
        self._pbp_cache: dict[str, list[dict]] = {}

    def _throttled(self) -> bool:
        """True when a remote call is allowed; updates the timestamp if so."""
        now = time.monotonic()
        if now - self._last_call < self.min_interval:
            return False
        self._last_call = now
        return True

    def scoreboard(self) -> list[dict]:
        """Today's games (cached within the polling interval)."""
        if self._throttled() or not self._scoreboard_cache:
            self._scoreboard_cache = fetch_live_scoreboard()
        return self._scoreboard_cache

    def play_by_play(self, game_id: str) -> list[dict]:
        """Actions so far for one game (cached within the polling interval)."""
        if self._throttled() or game_id not in self._pbp_cache:
            self._pbp_cache[game_id] = fetch_live_play_by_play(game_id)
        return self._pbp_cache[game_id]
