"""Unit tests for the live-format -> stats-format event adapter."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
from nba_api.stats.endpoints import playbyplayv3, scoreboardv3

from hoops_lab.ingestion.live import (
    adapt_live_actions,
    fetch_stats_play_by_play,
    fetch_stats_scoreboard,
    game_label,
    nba_today,
    pickable_games,
)


def _game(game_id: str, status: int, text: str) -> dict:
    return {
        "gameId": game_id,
        "gameStatus": status,
        "gameStatusText": text,
        "awayTeam": {"teamTricode": "CLE", "teamId": 1},
        "homeTeam": {"teamTricode": "PHI", "teamId": 2},
    }


def test_pickable_games_lists_in_progress_first_then_finals() -> None:
    games = [
        _game("final_a", 3, "Final"),
        _game("scheduled", 1, "7:00 pm ET"),
        _game("live", 2, "Q3 5:32"),
        _game("final_b", 3, "Final/OT"),
    ]

    picked = pickable_games(games)

    assert list(picked) == ["live", "final_a", "final_b"]
    assert game_label(picked["live"]) == "CLE @ PHI — Q3 5:32"


def test_nba_today_is_the_eastern_date_and_late_games_stay_on_their_night() -> None:
    # 7 pm ET tip = 01:00 in Italy the next day: still the ET date.
    assert nba_today(pd.Timestamp("2026-10-23 01:00", tz="Europe/Rome")) == date(2026, 10, 22)
    # A 10:30 pm ET tip is still in progress at 00:30 ET: keep the previous night.
    assert nba_today(pd.Timestamp("2026-10-23 00:30", tz="America/New_York")) == date(2026, 10, 22)
    assert nba_today(pd.Timestamp("2026-10-23 12:00", tz="America/New_York")) == date(2026, 10, 23)


def test_fetch_stats_scoreboard_queries_the_given_date_through_the_client() -> None:
    client = MagicMock()
    client._call.return_value.get_dict.return_value = {"scoreboard": {"games": [{"gameId": "1"}]}}

    games = fetch_stats_scoreboard(client, date(2026, 10, 21))

    client._call.assert_called_once_with(scoreboardv3.ScoreboardV3, game_date="2026-10-21")
    assert games == [{"gameId": "1"}]


def test_fetch_stats_play_by_play_uses_pbpv3_through_the_client() -> None:
    client = MagicMock()
    client.fetch_df.return_value = pd.DataFrame({"gameId": ["1"]})

    events = fetch_stats_play_by_play(client, "1")

    client.fetch_df.assert_called_once_with(playbyplayv3.PlayByPlayV3, game_id="1")
    assert events["gameId"].tolist() == ["1"]


def test_adapt_live_actions_maps_to_stats_format() -> None:
    actions = [
        {
            "actionNumber": 2,
            "period": 1,
            "clock": "PT11M30.00S",
            "teamId": 10,
            "actionType": "2pt",
            "subType": "Jump Shot",
            "shotResult": "Made",
            "scoreHome": "2",
            "scoreAway": "0",
            "description": "Jump Shot (2 PTS)",
        },
        {
            "actionNumber": 3,
            "period": 1,
            "clock": "PT11M10.00S",
            "teamId": 20,
            "actionType": "3pt",
            "subType": "Pullup",
            "shotResult": "Missed",
            "scoreHome": "",
            "scoreAway": "",
            "description": "MISS 3PT pullup",
        },
        {
            "actionNumber": 4,
            "period": 1,
            "clock": "PT11M08.00S",
            "teamId": 10,
            "actionType": "rebound",
            "subType": "defensive",
            "description": "REBOUND",
        },
        {
            "actionNumber": 5,
            "period": 1,
            "clock": "PT10M40.00S",
            "teamId": 10,
            "actionType": "turnover",
            "subType": "bad pass",
            "description": "TO",
        },
        {
            "actionNumber": 6,
            "period": 1,
            "clock": "PT10M20.00S",
            "teamId": 20,
            "actionType": "freethrow",
            "subType": "1 of 2",
            "shotResult": "Missed",
            "description": "Free Throw 1 of 2",
        },
        {
            "actionNumber": 7,
            "period": 1,
            "clock": "PT00M00.00S",
            "actionType": "period",
            "subType": "end",
            "description": "",
        },
    ]

    events = adapt_live_actions(actions, game_id="LIVE1")

    assert events["actionType"].tolist() == [
        "Made Shot",
        "Missed Shot",
        "Rebound",
        "Turnover",
        "Free Throw",
        "period",
    ]
    assert events["shotValue"].tolist()[:2] == [2, 3]
    assert events.iloc[4]["subType"] == "Free Throw 1 of 2"
    assert "MISS" in events.iloc[4]["description"]  # missed FT marker for the parser
    assert (events["gameId"] == "LIVE1").all()


def test_adapter_passes_shot_coordinates_through() -> None:
    actions = [
        {
            "actionNumber": 2,
            "period": 1,
            "clock": "PT11M30.00S",
            "teamId": 10,
            "actionType": "3pt",
            "subType": "Jump Shot",
            "shotResult": "Made",
            "xLegacy": -220,
            "yLegacy": 30,
            "playerName": "Doncic",
            "shotDistance": 23.5,
            "description": "3PT (Irving 2 AST)",
        }
    ]
    events = adapt_live_actions(actions, game_id="LIVE2")

    row = events.iloc[0]
    assert row["xLegacy"] == -220
    assert row["yLegacy"] == 30
    assert row["playerName"] == "Doncic"
    assert row["shotDistance"] == 23.5
