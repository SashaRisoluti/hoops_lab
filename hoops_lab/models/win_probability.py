"""In-game win probability from score margin and time remaining.

Logistic regression on (margin, margin / sqrt(time+1)) — the classic
time-discounted lead. Trained on the ingested play-by-play sample, so the
model is MVP-grade by construction (24 games, reference-team biased); the
integration suite gates it with a held-out-games AUC check. League-scale
training arrives when PBP coverage is extended.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from hoops_lab.features.possession import _clock_seconds, sort_chronological

REGULATION_MINUTES = 48.0


def _add_features(states: pd.DataFrame) -> pd.DataFrame:
    out = states.copy()
    out["margin_time"] = out["margin"] / np.sqrt(out["minutes_remaining"] + 1.0)
    return out


def build_game_states(events: pd.DataFrame, home_won: dict[str, bool]) -> pd.DataFrame:
    """One (margin, minutes_remaining, home_won) sample per scoring update.

    Parameters
    ----------
    events:
        PBPv3-format events (any number of games).
    home_won:
        game_id -> True when the home team won (the training label).
    """
    rows = []
    for game_id, game in events.groupby("gameId", sort=False):
        if str(game_id) not in {str(k) for k in home_won}:
            continue
        game = sort_chronological(game)
        home_score = pd.to_numeric(game["scoreHome"], errors="coerce")
        away_score = pd.to_numeric(game["scoreAway"], errors="coerce")
        clock_min = _clock_seconds(game["clock"]) / 60.0
        scoring = home_score.notna() & away_score.notna()
        for idx in game.index[scoring]:
            period = int(game.loc[idx, "period"])
            remaining_in_period = float(clock_min.loc[idx] or 0.0)
            if period <= 4:
                minutes_remaining = (4 - period) * 12.0 + remaining_in_period
            else:  # overtime: count down the extra period only
                minutes_remaining = remaining_in_period
            rows.append(
                {
                    "game_id": str(game_id),
                    "margin": float(home_score.loc[idx] - away_score.loc[idx]),
                    "minutes_remaining": minutes_remaining,
                    "home_won": bool(home_won[str(game_id)]),
                }
            )
    return pd.DataFrame(rows)


def build_states_from_db(db) -> pd.DataFrame:
    """Game states for every ingested PBP game, labelled from final scores."""
    events = db.query_df("SELECT * FROM play_by_play")
    finals = db.query_df(
        "SELECT game_id, home_pts, away_pts FROM games "
        "WHERE game_id IN (SELECT DISTINCT gameId FROM play_by_play)"
    )
    labels = {
        str(row["game_id"]): bool(row["home_pts"] > row["away_pts"]) for _, row in finals.iterrows()
    }
    return build_game_states(events, labels)


def train_win_probability(states: pd.DataFrame) -> LogisticRegression:
    """Fit P(home win | margin, time) on game-state samples."""
    featured = _add_features(states)
    model = LogisticRegression(max_iter=1000)
    model.fit(featured[["margin", "margin_time"]], featured["home_won"].astype(int))
    return model


def predict_wp_frame(model: LogisticRegression, states: pd.DataFrame) -> np.ndarray:
    """Home win probability for a frame of (margin, minutes_remaining) rows."""
    featured = _add_features(states)
    return model.predict_proba(featured[["margin", "margin_time"]])[:, 1]


def predict_wp(model: LogisticRegression, margin: float, minutes_remaining: float) -> float:
    """Home win probability for a single game state."""
    frame = pd.DataFrame({"margin": [margin], "minutes_remaining": [minutes_remaining]})
    return float(predict_wp_frame(model, frame)[0])
