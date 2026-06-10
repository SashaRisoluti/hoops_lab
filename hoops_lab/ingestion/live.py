"""Live data: nba_api live endpoints + the live->stats format adapter.

The live feed uses lowercase action types ("2pt", "3pt", "rebound", ...);
``adapt_live_actions`` converts them to the stats-format contract that the
possession parser and GameState expect, so live games run through the very
same pipeline as the replay simulation.

NOTE: live endpoints can only be exercised while NBA games are actually in
progress; the adapter mapping is unit-tested against the documented payload
shape and should be re-verified on a live game night.
"""

from __future__ import annotations

import pandas as pd

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
            }
        )
    return pd.DataFrame(rows)


def fetch_live_scoreboard() -> list[dict]:
    """Today's games from the live scoreboard (network)."""
    from nba_api.live.nba.endpoints import scoreboard

    return scoreboard.ScoreBoard().get_dict()["scoreboard"]["games"]


def fetch_live_play_by_play(game_id: str) -> list[dict]:
    """All actions so far for a live game (network)."""
    from nba_api.live.nba.endpoints import playbyplay

    return playbyplay.PlayByPlay(game_id).get_dict()["game"]["actions"]
