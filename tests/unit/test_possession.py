"""Unit tests for the possession parser (synthetic PBPv3 game, exact walk)."""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.possession import build_possessions

HOME, AWAY = 10, 20


def _ev(
    action_number: int,
    action_type: str,
    team_id: int = 0,
    sub_type: str = "",
    score: tuple[int, int] | None = None,
    description: str = "",
    period: int = 1,
) -> dict:
    return {
        "gameId": "g1",
        "actionNumber": action_number,
        "period": period,
        "clock": "PT06M00.00S",  # constant: actionNumber breaks the tie
        "teamId": team_id,
        "location": "h" if team_id == HOME else ("v" if team_id == AWAY else ""),
        "actionType": action_type,
        "subType": sub_type,
        "shotResult": "",
        "description": description,
        "scoreHome": str(score[0]) if score else "",
        "scoreAway": str(score[1]) if score else "",
    }


def test_full_synthetic_game_walkthrough() -> None:
    events = pd.DataFrame(
        [
            _ev(1, "period", sub_type="start"),
            # P1: home makes a two.
            _ev(2, "Made Shot", HOME, "Jump Shot", score=(2, 0)),
            # P2: away misses, home defensive rebound.
            _ev(3, "Missed Shot", AWAY, "Jump Shot"),
            _ev(4, "Rebound", HOME, "Unknown"),
            # P3: home turnover.
            _ev(5, "Turnover", HOME, "Bad Pass"),
            # P4: away misses, away OFFENSIVE rebound (possession continues), away makes a three.
            _ev(6, "Missed Shot", AWAY, "Jump Shot"),
            _ev(7, "Rebound", AWAY, "Unknown"),
            _ev(8, "Made Shot", AWAY, "Jump Shot", score=(2, 3)),
            # P5: away shooting foul drawn -> FT 1/2 made, 2/2 missed, home def rebound.
            _ev(9, "Foul", HOME, "Shooting"),
            _ev(10, "Free Throw", AWAY, "Free Throw 1 of 2", score=(2, 4)),
            _ev(11, "Free Throw", AWAY, "Free Throw 2 of 2", description="MISS FT 2 of 2"),
            _ev(12, "Rebound", HOME, "Unknown"),
            # P6: home holds for the period buzzer.
            _ev(13, "period", sub_type="end"),
        ]
    )

    possessions = build_possessions(events)

    assert possessions["possession_number"].tolist() == [1, 2, 3, 4, 5, 6]
    assert possessions["offense_team_id"].tolist() == [HOME, AWAY, HOME, AWAY, AWAY, HOME]
    assert possessions["points"].tolist() == [2, 0, 0, 3, 1, 0]
    assert possessions["ended_by"].tolist() == [
        "made_fg",
        "def_rebound",
        "turnover",
        "made_fg",
        "def_rebound",
        "period",
    ]


def test_and_one_stays_one_possession() -> None:
    events = pd.DataFrame(
        [
            _ev(1, "period", sub_type="start"),
            _ev(2, "Made Shot", HOME, "Driving Layup Shot", score=(2, 0)),
            _ev(3, "Foul", AWAY, "Shooting"),
            _ev(4, "Free Throw", HOME, "Free Throw 1 of 1", score=(3, 0)),
            _ev(5, "period", sub_type="end"),
        ]
    )

    possessions = build_possessions(events)

    assert len(possessions) == 1
    assert possessions.iloc[0]["points"] == 3  # the and-one is a single 3-point trip
    assert possessions.iloc[0]["ended_by"] == "made_ft"


def test_technical_free_throw_does_not_end_possession() -> None:
    events = pd.DataFrame(
        [
            _ev(1, "period", sub_type="start"),
            _ev(2, "Missed Shot", HOME, "Jump Shot"),
            _ev(3, "Rebound", HOME, "Unknown"),  # offensive board, same possession
            _ev(4, "Foul", AWAY, "Technical"),
            _ev(5, "Free Throw", HOME, "Free Throw Technical", score=(1, 0)),
            _ev(6, "Made Shot", HOME, "Jump Shot", score=(3, 0)),
            _ev(7, "period", sub_type="end"),
        ]
    )

    possessions = build_possessions(events)

    assert len(possessions) == 1
    assert possessions.iloc[0]["points"] == 3  # technical FT + the field goal
    assert possessions.iloc[0]["ended_by"] == "made_fg"
