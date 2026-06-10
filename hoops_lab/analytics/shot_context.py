"""Shot context from play-by-play: assisted share of made shots.

ShotChartDetail carries no assisted flag; play-by-play descriptions do
("... (Irving 4 AST)"). Joining on (GAME_ID, GAME_EVENT_ID) ==
(gameId, actionNumber) recovers it for every game with PBP coverage —
currently the sampled games; the share extends automatically as more
play-by-play is downloaded.
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.storage.database import Database


def assisted_summary(db: Database, shots: pd.DataFrame) -> dict | None:
    """Assisted share of the made shots covered by play-by-play.

    Parameters
    ----------
    db:
        Database with a ``play_by_play`` table.
    shots:
        Filtered shots (needs GAME_ID, GAME_EVENT_ID, SHOT_MADE_FLAG).

    Returns
    -------
    Dict with made_covered / assisted / share / games_covered, or None when
    no shot matches the play-by-play coverage.
    """
    if shots.empty or not db.has_table("play_by_play"):
        return None

    con = db.connect()
    con.register("shots_selection", shots[["GAME_ID", "GAME_EVENT_ID", "SHOT_MADE_FLAG"]])
    matched = db.query_df(
        """
        SELECT s.SHOT_MADE_FLAG, p.gameId, p.description
        FROM shots_selection AS s
        JOIN play_by_play AS p
          ON p.gameId = s.GAME_ID AND p.actionNumber = s.GAME_EVENT_ID
        """
    )
    if matched.empty:
        return None

    made = matched.loc[matched["SHOT_MADE_FLAG"] == 1]
    if made.empty:
        return None

    assisted = made["description"].astype(str).str.contains(" AST)", regex=False)
    return {
        "made_covered": int(len(made)),
        "assisted": int(assisted.sum()),
        "share": float(assisted.mean()),
        "games_covered": int(matched["gameId"].nunique()),
    }
