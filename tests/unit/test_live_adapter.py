"""Unit tests for the live-format -> stats-format event adapter."""

from __future__ import annotations

from hoops_lab.ingestion.live import adapt_live_actions


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
