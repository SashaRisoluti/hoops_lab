"""In-game win probability as a drifting lead, with leak-free pregame net-rating priors.

Expected final home margin = current margin + pregame drift x remaining fraction, with the
uncertainty shrinking as the square root of that fraction. In logistic form, no intercept::

    f = max(seconds_remaining, 1) / 2880
    z = a * margin / sqrt(f) + b * sqrt(f) * (1 - neutral) + c * prior_diff * sqrt(f)
    P(home wins) = 1 / (1 + exp(-z))

``prior_diff`` is the home-minus-away pregame net rating: the season-to-date value (games
strictly before the game date) blended with last season's final value,
``(n * nr_to_date + k * nr_last_season) / (n + k)``. Training priors and the exported current
priors share the same helpers, so training and inference agree. Training margins are summed
from scoring events, never from the feed's ``scoreHome``/``scoreAway`` snapshots (see
``hoops_lab.features.possession``).

Imported by ``scripts/`` and tests only — never by ``dashboard/``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from hoops_lab.features.possession import _clock_seconds, _event_points, sort_chronological

REGULATION_SECONDS = 2880.0
PERIOD_SECONDS = 720.0
#: Weight (in games) of last season's final net rating in the pregame prior.
PRIOR_GAMES_K = 10.0

STATE_COLUMNS = [
    "game_id",
    "season",
    "margin",
    "seconds_remaining",
    "neutral",
    "prior_diff",
    "home_won",
]


def team_game_ratings(box: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game: points, opponent points and the game's possessions.

    A team's possessions are estimated as ``FGA + 0.44*FTA - OREB + TOV``; ``poss`` is the
    mean of both teams' estimates. ``GAME_DATE`` is normalised to a timestamp. Games without
    exactly two team rows are dropped.
    """
    out = box[["GAME_ID", "TEAM_ID", "TEAM_ABBREVIATION", "GAME_DATE", "season"]].copy()
    out["GAME_ID"] = out["GAME_ID"].astype(str)
    out["GAME_DATE"] = pd.to_datetime(out["GAME_DATE"])
    out["pts"] = box["PTS"]
    team_poss = box["FGA"] + 0.44 * box["FTA"] - box["OREB"] + box["TOV"]
    by_game = out.groupby("GAME_ID")["pts"]
    out["opp_pts"] = by_game.transform("sum") - out["pts"]
    out["poss"] = team_poss.groupby(out["GAME_ID"]).transform("mean")
    return out.loc[by_game.transform("size") == 2].reset_index(drop=True)


def _ratings_with_diff(box: pd.DataFrame) -> pd.DataFrame:
    ratings = team_game_ratings(box)
    ratings["diff"] = ratings["pts"] - ratings["opp_pts"]
    return ratings


def _net_rating(diff: pd.Series, poss: pd.Series) -> pd.Series:
    """Points per 100 possessions; NaN (never inf) without possessions."""
    return 100.0 * diff / poss.where(poss > 0)


def _next_season(season: str) -> str:
    """'2021-22' -> '2022-23'."""
    start = int(season[:4]) + 1
    return f"{start}-{(start + 1) % 100:02d}"


def _last_season_nr(ratings: pd.DataFrame, rows: pd.DataFrame) -> np.ndarray:
    """Each row's team final net rating of the season before the row's season (0 if absent)."""
    finals = ratings.groupby(["TEAM_ID", "season"])[["diff", "poss"]].sum()
    last = _net_rating(finals["diff"], finals["poss"]).rename("nr_last").reset_index()
    last["season"] = last["season"].map(_next_season)  # the season it is "last season" for
    merged = rows[["TEAM_ID", "season"]].merge(last, on=["TEAM_ID", "season"], how="left")
    return merged["nr_last"].fillna(0.0).to_numpy()


def _blend(n: pd.Series, nr_to_date: pd.Series, nr_last: pd.Series, k: float) -> pd.Series:
    """Shrink the season-to-date rating towards last season's: (n*NR + k*NR_last)/(n + k)."""
    return (n * nr_to_date.fillna(0.0) + k * nr_last) / (n + k)


def pregame_priors(box: pd.DataFrame, k: float = PRIOR_GAMES_K) -> pd.DataFrame:
    """Leak-free pregame net rating of every team-game in ``box_scores_team`` rows.

    Season-to-date totals use only same-season games with ``GAME_DATE`` strictly before the
    game's date (so a same-date game never sees another). The first season in the data has
    a last-season rating of 0.

    Returns ``GAME_ID, TEAM_ID, n_prior, nr_to_date, nr_last_season, prior``
    (``nr_to_date`` is NaN when ``n_prior`` is 0).
    """
    ratings = _ratings_with_diff(box)
    keys = ["TEAM_ID", "season", "GAME_DATE"]
    daily = ratings.groupby(keys).agg(
        diff=("diff", "sum"), poss=("poss", "sum"), n=("diff", "size")
    )
    # Running team-season totals minus the date's own games = totals strictly before the date.
    before = (daily.groupby(level=["TEAM_ID", "season"]).cumsum() - daily).reset_index()
    out = ratings[["GAME_ID", *keys]].merge(before, on=keys, how="left")
    out["n_prior"] = out["n"].astype(int)
    out["nr_to_date"] = _net_rating(out["diff"], out["poss"])
    out["nr_last_season"] = _last_season_nr(ratings, out)
    out["prior"] = _blend(out["n_prior"], out["nr_to_date"], out["nr_last_season"], k)
    return out[["GAME_ID", "TEAM_ID", "n_prior", "nr_to_date", "nr_last_season", "prior"]]


def current_priors(
    box: pd.DataFrame, season: str, k: float = PRIOR_GAMES_K
) -> tuple[dict[str, float], str]:
    """Tricode -> prior after every game of ``season``, plus the as-of date (``YYYY-MM-DD``)."""
    ratings = _ratings_with_diff(box)
    current = ratings.loc[ratings["season"] == season].sort_values("GAME_DATE")
    if current.empty:
        raise ValueError(f"no box scores for season {season}")
    totals = (
        current.groupby("TEAM_ID")
        .agg(
            diff=("diff", "sum"),
            poss=("poss", "sum"),
            n=("diff", "size"),
            tricode=("TEAM_ABBREVIATION", "last"),
        )
        .reset_index()
        .assign(season=season)
    )
    nr_last = pd.Series(_last_season_nr(ratings, totals), index=totals.index)
    prior = _blend(totals["n"], _net_rating(totals["diff"], totals["poss"]), nr_last, k)
    as_of = current["GAME_DATE"].max().strftime("%Y-%m-%d")
    return dict(zip(totals["tricode"], prior.astype(float), strict=True)), as_of


def build_states(pbp: pd.DataFrame, games: pd.DataFrame, priors: pd.DataFrame) -> pd.DataFrame:
    """Training states: an opening state per game plus one per scoring event.

    Parameters
    ----------
    pbp:
        PlayByPlayV3 events (gameId, actionNumber, period, clock, teamId, actionType,
        description, shotValue).
    games:
        ``games`` rows (game_id, season, home_team_id, away_team_id, home_pts, away_pts,
        neutral_site) — the label and the home side.
    priors:
        ``pregame_priors`` output (GAME_ID, TEAM_ID, prior). Games lacking either team's
        prior are dropped.

    Returns ``game_id, season, margin, seconds_remaining, neutral, prior_diff, home_won``.
    The margin (home - away) is summed from scoring events; overtime counts down the extra
    period only.
    """
    prior = priors[["GAME_ID", "TEAM_ID", "prior"]].assign(GAME_ID=priors["GAME_ID"].astype(str))
    meta = games.assign(
        game_id=games["game_id"].astype(str),
        neutral=games["neutral_site"].astype(bool),
        home_won=games["home_pts"] > games["away_pts"],
    )
    for side in ("home", "away"):
        side_prior = prior.rename(
            columns={"GAME_ID": "game_id", "TEAM_ID": f"{side}_team_id", "prior": f"{side}_prior"}
        )
        meta = meta.merge(side_prior, on=["game_id", f"{side}_team_id"])
    meta["prior_diff"] = meta["home_prior"] - meta["away_prior"]

    pbp = pbp.assign(gameId=pbp["gameId"].astype(str))
    pbp = pbp.loc[pbp["gameId"].isin(meta["game_id"])]
    events = pd.concat(
        [sort_chronological(game) for _, game in pbp.groupby("gameId", sort=False)],
        ignore_index=True,
    )
    home = events["gameId"].map(meta.set_index("game_id")["home_team_id"])
    team = events["teamId"].fillna(0)
    points = _event_points(events)
    signed = points.where(team == home, 0) - points.where((team > 0) & (team != home), 0)
    margin = signed.groupby(events["gameId"]).cumsum()

    scored = points > 0
    clock = _clock_seconds(events.loc[scored, "clock"])
    periods_left = (4 - events.loc[scored, "period"].astype(int)).clip(lower=0)
    scoring_states = pd.DataFrame(
        {
            "game_id": events.loc[scored, "gameId"],
            "margin": margin[scored].astype(float),
            "seconds_remaining": periods_left * PERIOD_SECONDS + clock,
        }
    )
    opening = pd.DataFrame(
        {
            "game_id": events["gameId"].unique(),
            "margin": 0.0,
            "seconds_remaining": REGULATION_SECONDS,
        }
    )
    states = pd.concat([opening, scoring_states]).sort_values("game_id", kind="stable")
    states = states.merge(meta[["game_id", "season", "neutral", "prior_diff", "home_won"]])
    return states[STATE_COLUMNS].reset_index(drop=True)


def features(states: pd.DataFrame) -> np.ndarray:
    """Model inputs ``[margin/sqrt(f), sqrt(f)*(1 - neutral), prior_diff*sqrt(f)]``.

    ``f = max(seconds_remaining, 1) / 2880`` — floored at one second, so never inf.
    """
    f = np.maximum(states["seconds_remaining"].to_numpy(float), 1.0) / REGULATION_SECONDS
    root = np.sqrt(f)
    return np.column_stack(
        [
            states["margin"].to_numpy(float) / root,
            root * (1.0 - states["neutral"].to_numpy(float)),
            states["prior_diff"].to_numpy(float) * root,
        ]
    )


def fit(states: pd.DataFrame) -> LogisticRegression:
    """Unpenalised, intercept-free logistic fit of ``home_won`` on ``features(states)``.

    ``C=np.inf`` is the no-penalty fit (``penalty=None`` is deprecated since scikit-learn 1.8).
    """
    model = LogisticRegression(fit_intercept=False, C=np.inf, max_iter=1000)
    return model.fit(features(states), states["home_won"].astype(int))


def predict(model: LogisticRegression, states: pd.DataFrame) -> np.ndarray:
    """Home win probability of each state."""
    return model.predict_proba(features(states))[:, 1]


def coefficients(model: LogisticRegression) -> dict[str, float]:
    """Raw coefficients plus readable ones: home court and net-rating drift in points, scale."""
    a, b, c = (float(value) for value in model.coef_[0])

    def per_a(value: float) -> float:
        return value / a if a else float("nan")

    return {
        "a": a,
        "b": b,
        "c": c,
        "homeCourtPts": per_a(b),
        "pointsPerNetRating": per_a(c),
        "scale": per_a(1.0),
    }


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Equal-width-bin ECE: sum over bins of (n_b / N) * |mean(y_b) - mean(p_b)|.

    That equals sum_b |sum(y_b) - sum(p_b)| / N. NaN for empty input.
    """
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if p.size == 0:
        return float("nan")
    index = np.clip((p * bins).astype(int), 0, bins - 1)
    gap = np.bincount(index, weights=y, minlength=bins) - np.bincount(
        index, weights=p, minlength=bins
    )
    return float(np.abs(gap).sum() / p.size)
