"""Possession segmentation from PlayByPlayV3 events, with per-possession points.

Possession-ending rules (deliberate simplifications, validated by the
score-reconstruction invariant in the integration suite):

* made field goal — unless an and-one free throw ("1 of 1" by the same team)
  is pending, in which case the trip ends at that free throw;
* turnover;
* defensive rebound — a rebound by a team different from the last missing
  team (PBPv3 rebound subTypes are mostly "Unknown", so offensive vs
  defensive is inferred by comparing team ids);
* made final free throw ("N of N", neither technical nor flagrant);
* period end.

Points are the offense team's points between possession start and end, summed
from its own scoring events (made field goals at ``shotValue``, made free
throws); the home side is identified via the ``location`` column. The feed's
``scoreHome``/``scoreAway`` snapshots are deliberately NOT used: a scorer
correction is entered later carrying the scoreboard of its insertion time, so
once sorted back to its real time the snapshot series runs backwards. Summed
events reproduce the box score exactly on every sampled game; snapshots did not.
KNOWN LIMIT: points scored by the *defending* team inside a possession
(technical free throws) are not attributed to any possession (rare; bounded by
the integration test tolerance).

Run as a module to (re)build the ``possessions`` table from the ingested
play-by-play sample::

    python -m hoops_lab.features.possession
"""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

#: Events that can belong to an offensive sequence.
_OFFENSIVE_ACTIONS = {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}

#: Events skipped when looking ahead for an and-one free throw.
_LOOKAHEAD_SKIP = {
    "Foul",
    "Substitution",
    "Timeout",
    "Instant Replay",
    "Violation",
    "Ejection",
    "Jump Ball",
}

_FINAL_FT = re.compile(r"Free Throw (\d) of \1$")

_CLOCK = re.compile(r"PT(\d+)M([\d.]+)S")


def _clock_seconds(clock: pd.Series) -> pd.Series:
    """Seconds remaining in the period from a 'PT06M41.00S' style clock."""
    extracted = clock.astype(str).str.extract(_CLOCK)
    return pd.to_numeric(extracted[0], errors="coerce") * 60 + pd.to_numeric(
        extracted[1], errors="coerce"
    )


def sort_chronological(game: pd.DataFrame) -> pd.DataFrame:
    """Order one game's events chronologically.

    Raw feeds occasionally contain late-inserted rows with out-of-order
    actionNumbers (events from a previous period in the middle of the next
    one), which would make the cumulative score go backwards. True order is
    period asc, game clock desc, actionNumber as the tiebreak.
    """
    ordered = game.sort_values("actionNumber").reset_index(drop=True)
    ordered["_clock_sec"] = _clock_seconds(ordered["clock"]).ffill().fillna(720.0)
    ordered = ordered.sort_values(
        ["period", "_clock_sec", "actionNumber"], ascending=[True, False, True]
    )
    return ordered.drop(columns="_clock_sec").reset_index(drop=True)


def _event_points(game: pd.DataFrame) -> pd.Series:
    """Points scored on each event: made field goals at ``shotValue``, made free throws 1."""
    made_fg = game["actionType"].eq("Made Shot")
    missed = game["description"].astype(str).str.contains("MISS")
    made_ft = game["actionType"].eq("Free Throw") & ~missed
    shot_value = pd.to_numeric(game["shotValue"], errors="coerce").fillna(0)
    return shot_value.where(made_fg, 0) + made_ft.astype(int)


def _and_one_pending(game: pd.DataFrame, index: int, team: int) -> bool:
    """True when a '1 of 1' free throw by ``team`` follows a made shot."""
    for j in range(index + 1, min(index + 8, len(game))):
        nxt = game.iloc[j]
        if nxt["actionType"] in _LOOKAHEAD_SKIP:
            continue
        return (
            nxt["actionType"] == "Free Throw"
            and "1 of 1" in str(nxt["subType"])
            and int(nxt["teamId"] or 0) == team
        )
    return False


def _segment_game(
    game_id: str,
    game: pd.DataFrame,
    home_id: int,
    home_score: pd.Series,
    away_score: pd.Series,
) -> list[dict]:
    """Walk one game's chronologically-ordered events into possession rows."""
    results: list[dict] = []
    offense: int | None = None
    last_miss_team: int | None = None
    start_home, start_away = 0.0, 0.0
    number = 0

    def end_possession(index: int, ended_by: str, offense_team: int) -> None:
        nonlocal number, start_home, start_away, last_miss_team
        number += 1
        if offense_team == home_id:
            points = home_score.iloc[index] - start_home
        else:
            points = away_score.iloc[index] - start_away
        results.append(
            {
                "game_id": game_id,
                "possession_number": number,
                "offense_team_id": offense_team,
                "period": int(game.iloc[index]["period"]),
                "points": int(round(points)),
                "ended_by": ended_by,
            }
        )
        start_home, start_away = home_score.iloc[index], away_score.iloc[index]
        last_miss_team = None

    for i in range(len(game)):
        event = game.iloc[i]
        action = event["actionType"]
        sub_type = str(event["subType"] or "")
        team = int(event["teamId"] or 0)

        if action == "period" and sub_type == "end":
            if offense is not None:
                end_possession(i, "period", offense)
                offense = None
            continue

        if action == "Free Throw" and ("Technical" in sub_type or "Flagrant" in sub_type):
            # Technical/flagrant FTs never end a possession; points by the
            # current offense are still captured via the score delta.
            continue

        if action in _OFFENSIVE_ACTIONS and team > 0:
            if offense is None:
                offense = team
            elif team != offense and action in ("Made Shot", "Missed Shot", "Turnover"):
                offense = team  # resync (e.g. steal without an explicit change marker)

        if action == "Made Shot" and team > 0:
            if not _and_one_pending(game, i, team):
                end_possession(i, "made_fg", team)
                offense = None

        elif action == "Missed Shot" and team > 0:
            last_miss_team = team

        elif action == "Free Throw" and team > 0:
            missed = "MISS" in str(event["description"] or "")
            if _FINAL_FT.search(sub_type):
                if missed:
                    last_miss_team = team
                else:
                    end_possession(i, "made_ft", team)
                    offense = None

        elif action == "Turnover" and team > 0:
            end_possession(i, "turnover", team)
            offense = None

        elif action == "Rebound" and team > 0:
            if last_miss_team is not None and team != last_miss_team:
                end_possession(i, "def_rebound", last_miss_team)
                offense = team  # the rebounding team starts the next trip
            else:
                last_miss_team = None  # offensive board: same possession

    return results


def build_possessions(pbp: pd.DataFrame) -> pd.DataFrame:
    """Segment play-by-play events into possessions with points and end reason.

    Parameters
    ----------
    pbp:
        PlayByPlayV3 rows (one or many games); required columns: gameId,
        actionNumber, period, clock, teamId, location, actionType, subType,
        description, shotValue.

    Returns
    -------
    One row per possession: game_id, possession_number, offense_team_id,
    period, points, ended_by.
    """
    results: list[dict] = []

    for game_id, game in pbp.groupby("gameId", sort=False):
        game = sort_chronological(game)

        home_rows = game.loc[(game["location"] == "h") & (game["teamId"].fillna(0) > 0)]
        if home_rows.empty:
            logger.warning("game %s: cannot identify the home team — skipped", game_id)
            continue
        home_id = int(home_rows.iloc[0]["teamId"])

        # Running totals from the scoring events, not the feed's scoreHome/scoreAway:
        # a scorer correction carries the scoreboard of its insertion time, so once sorted
        # back to its real time that snapshot is non-monotonic (0022600009 was off by 7).
        team = game["teamId"].fillna(0).astype(int)
        points = _event_points(game)
        home_score = points.where(team == home_id, 0).cumsum()
        away_score = points.where((team > 0) & (team != home_id), 0).cumsum()

        results.extend(_segment_game(str(game_id), game, home_id, home_score, away_score))

    return pd.DataFrame(
        results,
        columns=["game_id", "possession_number", "offense_team_id", "period", "points", "ended_by"],
    )


if __name__ == "__main__":
    import sys

    from hoops_lab.storage.database import Database

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    db = Database()
    pbp_events = db.query_df("SELECT * FROM play_by_play")
    possessions = build_possessions(pbp_events)

    # Replaces the empty structural table from the initial migration.
    db.connect().register("possessions_src", possessions)
    db.execute("CREATE OR REPLACE TABLE possessions AS SELECT * FROM possessions_src")

    summary = (
        possessions.groupby("game_id")
        .agg(possessions=("possession_number", "max"), points=("points", "sum"))
        .reset_index()
    )
    ppp = possessions["points"].sum() / len(possessions)
    print(f"{len(possessions):,} possessions across {len(summary)} games — PPP {ppp:.3f}")
    print(summary.to_string(index=False))
