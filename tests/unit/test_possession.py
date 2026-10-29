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
    shot_value: int = 0,
    clock: str = "PT06M00.00S",  # constant by default: actionNumber breaks the tie
) -> dict:
    return {
        "gameId": "g1",
        "actionNumber": action_number,
        "period": period,
        "clock": clock,
        "teamId": team_id,
        "location": "h" if team_id == HOME else ("v" if team_id == AWAY else ""),
        "actionType": action_type,
        "subType": sub_type,
        "shotResult": "",
        "shotValue": shot_value,
        "description": description,
        "scoreHome": str(score[0]) if score else "",
        "scoreAway": str(score[1]) if score else "",
    }


def test_full_synthetic_game_walkthrough() -> None:
    events = pd.DataFrame(
        [
            _ev(1, "period", sub_type="start"),
            # P1: home makes a two.
            _ev(2, "Made Shot", HOME, "Jump Shot", score=(2, 0), shot_value=2),
            # P2: away misses, home defensive rebound.
            _ev(3, "Missed Shot", AWAY, "Jump Shot"),
            _ev(4, "Rebound", HOME, "Unknown"),
            # P3: home turnover.
            _ev(5, "Turnover", HOME, "Bad Pass"),
            # P4: away misses, away OFFENSIVE rebound (possession continues), away makes a three.
            _ev(6, "Missed Shot", AWAY, "Jump Shot"),
            _ev(7, "Rebound", AWAY, "Unknown"),
            _ev(8, "Made Shot", AWAY, "Jump Shot", score=(2, 3), shot_value=3),
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
            _ev(2, "Made Shot", HOME, "Driving Layup Shot", score=(2, 0), shot_value=2),
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
            _ev(6, "Made Shot", HOME, "Jump Shot", score=(3, 0), shot_value=2),
            _ev(7, "period", sub_type="end"),
        ]
    )

    possessions = build_possessions(events)

    assert len(possessions) == 1
    assert possessions.iloc[0]["points"] == 3  # technical FT + the field goal
    assert possessions.iloc[0]["ended_by"] == "made_fg"


def test_late_inserted_corrections_do_not_shift_points() -> None:
    """Points come from the scoring events, never from the feed's score snapshot.

    A scorer correction is entered later and carries the scoreboard of its *insertion*
    time; sorted back to its real time, that snapshot belongs to the future, and events
    after it still show the uncorrected score. Real case: HOU @ SAS on 2026-10-23
    (0022600009) was credited +5 / -7 by score deltas while its events add up exactly.
    """
    events = pd.DataFrame(
        [
            _ev(1, "period", sub_type="start", clock="PT12M00.00S"),
            _ev(2, "Made Shot", HOME, "Jump Shot", (2, 0), shot_value=2, clock="PT11M00.00S"),
            _ev(3, "Made Shot", AWAY, "Layup Shot", (2, 2), shot_value=2, clock="PT10M00.00S"),
            _ev(4, "Made Shot", HOME, "Jump Shot", (5, 2), shot_value=3, clock="PT09M00.00S"),
            # Two free throws at 10:30, entered after the 9:00 basket with that later score.
            _ev(10, "Foul", HOME, "Shooting", clock="PT10M30.00S"),
            _ev(11, "Free Throw", AWAY, "Free Throw 1 of 2", (5, 3), clock="PT10M30.00S"),
            _ev(12, "Free Throw", AWAY, "Free Throw 2 of 2", (5, 4), clock="PT10M30.00S"),
            _ev(13, "period", sub_type="end", score=(5, 4), clock="PT00M00.00S"),
        ]
    )

    possessions = build_possessions(events)

    totals = possessions.groupby("offense_team_id")["points"].sum().to_dict()
    assert totals == {HOME: 5, AWAY: 4}
    assert (possessions["points"] >= 0).all()
