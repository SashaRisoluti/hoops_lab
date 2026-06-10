"""Unit tests for assisted-shot context (PBP join) and event shot frames."""

from __future__ import annotations

import pandas as pd

from hoops_lab.analytics.shot_context import assisted_summary
from hoops_lab.live.game_state import shot_frame_from_events
from hoops_lab.storage.database import Database


def test_assisted_summary_joins_pbp_descriptions() -> None:
    db = Database(path=":memory:")
    con = db.connect()
    con.register(
        "play_by_play",
        pd.DataFrame(
            {
                "gameId": ["g1", "g1", "g2"],
                "actionNumber": [2, 5, 9],
                "description": [
                    "Doncic 3PT Jump Shot (8 PTS) (Irving 4 AST)",
                    "Irving Driving Layup (12 PTS)",  # unassisted make
                    "Gafford Dunk (4 PTS) (Doncic 7 AST)",
                ],
            }
        ),
    )
    shots = pd.DataFrame(
        {
            "GAME_ID": ["g1", "g1", "g1", "g9"],
            "GAME_EVENT_ID": [2, 5, 7, 1],  # 7 has no PBP row, g9 not sampled
            "SHOT_MADE_FLAG": [1, 1, 1, 1],
        }
    )

    summary = assisted_summary(db, shots)

    assert summary is not None
    assert summary["made_covered"] == 2  # events 2 and 5 matched
    assert summary["assisted"] == 1
    assert summary["share"] == 0.5
    assert summary["games_covered"] == 1


def test_assisted_summary_returns_none_without_coverage() -> None:
    db = Database(path=":memory:")
    db.connect().register(
        "play_by_play",
        pd.DataFrame({"gameId": ["g1"], "actionNumber": [1], "description": ["x"]}),
    )
    shots = pd.DataFrame({"GAME_ID": ["g9"], "GAME_EVENT_ID": [5], "SHOT_MADE_FLAG": [1]})
    assert assisted_summary(db, shots) is None


def test_shot_frame_from_events_maps_and_flags_assists() -> None:
    events = pd.DataFrame(
        {
            "actionType": ["Made Shot", "Missed Shot", "Made Shot", "Made Shot", "Turnover"],
            "teamId": [10, 20, 10, 20, 10],
            "xLegacy": [10, -50, 200, None, None],
            "yLegacy": [20, 100, 50, None, None],
            "playerName": ["Doncic", "Brunson", "Irving", "Gafford", "Doncic"],
            "shotDistance": [2.0, 12.0, 22.0, 1.0, None],
            "subType": ["Layup", "Jump Shot", "Jump Shot", "Dunk", "Bad Pass"],
            "description": [
                "Doncic Layup (Irving 3 AST)",
                "MISS Brunson Jump Shot",
                "Irving Jump Shot",
                "Gafford Dunk (Doncic 8 AST)",
                "TO",
            ],
        }
    )

    frame = shot_frame_from_events(events)

    # The Turnover row and the shot without coordinates are excluded.
    assert len(frame) == 3
    assert frame["SHOT_MADE_FLAG"].tolist() == [1, 0, 1]
    assert frame["ASSISTED"].tolist() == [True, False, False]
    assert frame.iloc[0]["LOC_X"] == 10
    assert frame.iloc[0]["PLAYER_NAME"] == "Doncic"
