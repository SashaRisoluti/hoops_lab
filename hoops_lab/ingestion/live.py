"""Live data: nba_api live endpoints + the live->stats format adapter.

The live feed uses lowercase action types ("2pt", "3pt", "rebound", ...);
``adapt_live_actions`` converts them to the stats-format contract that the
possession parser and GameState expect, so live games run through the very
same pipeline as the replay simulation.

NOTE: live endpoints can only be exercised while NBA games are actually in
progress; the adapter mapping is unit-tested against the documented payload
shape and should be re-verified on a live game night.

The live CDN (cdn.nba.com) and stats.nba.com are blocked on different networks
(corporate proxies vs datacenter IPs), so the stats endpoints ScoreboardV3 and
PlayByPlayV3 serve as a fallback: the scoreboard payload has the same shape and
PBPv3 already is the stats-format contract.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from nba_api.stats.endpoints import playbyplayv3, scoreboardv3

from hoops_lab.config import NBA_API_TIMEOUT
from hoops_lab.ingestion.nba_api_client import NBAApiClient

#: Per-request timeout for live-page calls: short, so a blocked host cannot hang a refresh.
LIVE_TIMEOUT: int = min(10, NBA_API_TIMEOUT)

#: live actionType -> stats-format actionType (shots handled separately).
_SIMPLE_ACTIONS = {
    "rebound": "Rebound",
    "turnover": "Turnover",
    "freethrow": "Free Throw",
    "period": "period",
    "substitution": "Substitution",
    "timeout": "Timeout",
    "foul": "Foul",
    "jumpball": "Jump Ball",
    "violation": "Violation",
}


def adapt_live_actions(actions: list[dict], game_id: str) -> pd.DataFrame:
    """Convert live-feed actions to the stats-format event contract."""
    rows = []
    for action in actions:
        action_type = str(action.get("actionType", ""))
        shot_result = str(action.get("shotResult", ""))
        sub_type = str(action.get("subType", ""))
        description = str(action.get("description", ""))

        if action_type in ("2pt", "3pt"):
            mapped_type = "Made Shot" if shot_result == "Made" else "Missed Shot"
            shot_value = 3 if action_type == "3pt" else 2
        else:
            mapped_type = _SIMPLE_ACTIONS.get(action_type, action_type)
            shot_value = 0
            if action_type == "freethrow":
                sub_type = f"Free Throw {sub_type}" if sub_type else "Free Throw"
                if shot_result == "Missed" and "MISS" not in description:
                    description = f"MISS {description}"

        rows.append(
            {
                "gameId": game_id,
                "actionNumber": action.get("actionNumber"),
                "period": action.get("period"),
                "clock": action.get("clock", ""),
                "teamId": action.get("teamId", 0) or 0,
                "location": action.get("location", ""),
                "actionType": mapped_type,
                "subType": sub_type,
                "shotValue": shot_value,
                "description": description,
                "scoreHome": action.get("scoreHome", ""),
                "scoreAway": action.get("scoreAway", ""),
                # Shot-map passthrough (present on shot events in the live feed).
                "xLegacy": action.get("xLegacy", ""),
                "yLegacy": action.get("yLegacy", ""),
                "playerName": action.get("playerName", ""),
                "shotDistance": action.get("shotDistance", ""),
            }
        )
    return pd.DataFrame(rows)


def nba_today(now: pd.Timestamp | None = None) -> date:
    """The NBA game night in progress, as a US Eastern date.

    The night rolls over at 06:00 ET rather than midnight, so a late tip still in
    progress after midnight ET stays on its own night's scoreboard.
    """
    now = pd.Timestamp.now(tz="UTC") if now is None else now
    eastern = now.tz_convert("America/New_York")
    return (eastern - pd.Timedelta(hours=6)).date()


def pickable_games(games: list[dict]) -> dict[str, dict]:
    """In-progress games first, then finished ones, keyed by gameId (scheduled dropped)."""
    started = sorted(
        (g for g in games if g.get("gameStatus") in (2, 3)), key=lambda g: g["gameStatus"]
    )
    return {str(g["gameId"]): g for g in started}


def game_label(game: dict) -> str:
    """'AWY @ HOM — <status text>' picker label (status text: 'Q3 5:32', 'Final', ...)."""
    away, home = game["awayTeam"]["teamTricode"], game["homeTeam"]["teamTricode"]
    return f"{away} @ {home} — {str(game.get('gameStatusText', '')).strip()}"


def fetch_live_scoreboard() -> list[dict]:
    """Today's games from the live scoreboard (network)."""
    from nba_api.live.nba.endpoints import scoreboard

    return scoreboard.ScoreBoard(timeout=LIVE_TIMEOUT).get_dict()["scoreboard"]["games"]


def fetch_live_play_by_play(game_id: str) -> list[dict]:
    """All actions so far for a live game (network)."""
    from nba_api.live.nba.endpoints import playbyplay

    return playbyplay.PlayByPlay(game_id, timeout=LIVE_TIMEOUT).get_dict()["game"]["actions"]


def fetch_stats_scoreboard(client: NBAApiClient, game_date: date) -> list[dict]:
    """One night's games from stats.nba.com ScoreboardV3 (same shape as the live feed)."""
    endpoint = client._call(scoreboardv3.ScoreboardV3, game_date=game_date.isoformat())
    return endpoint.get_dict()["scoreboard"]["games"]


def fetch_stats_play_by_play(client: NBAApiClient, game_id: str) -> pd.DataFrame:
    """PlayByPlayV3 events so far for one game — already the stats-format contract."""
    return client.fetch_df(playbyplayv3.PlayByPlayV3, game_id=game_id)
