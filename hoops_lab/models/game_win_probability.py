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
from sklearn.metrics import log_loss

from hoops_lab.features.possession import _clock_seconds, _event_points, sort_chronological
from hoops_lab.models.win_probability import predict_wp_frame, train_win_probability
from hoops_lab.storage.database import Database

REGULATION_SECONDS = 2880.0
PERIOD_SECONDS = 720.0
#: Weight (in games) of last season's final net rating in the pregame prior.
PRIOR_GAMES_K = 10.0
#: Completed seasons held out by the quality gate; the seasons before them train.
HOLDOUT_SEASONS = 2
#: Regular-season games of a complete season (30 teams x 82 / 2).
SEASON_GAMES = 1230
#: Calibration ceiling of the gate (10 equal-width bins). Never relaxed.
MAX_ECE = 0.05
_EPS = 1e-15
_GATE_KEYS = {"holdoutLogLoss", "baselineLogLoss", "ece", "pregameLogLoss", "constantLogLoss"}

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
) -> tuple[dict[str, float], str | None]:
    """Tricode -> prior after every game of ``season``, plus the as-of date (``YYYY-MM-DD``).

    Every team of ``season`` or of the season before is included: a team without a game yet
    (n = 0) gets last season's final net rating. The as-of date is the latest game behind the
    priors (last season's final date before opening night); None without any game.
    """
    ratings = _ratings_with_diff(box)
    pool = ratings.loc[
        (ratings["season"] == season) | (ratings["season"].map(_next_season) == season)
    ].sort_values("GAME_DATE")
    if pool.empty:
        return {}, None
    tricodes = pool.groupby("TEAM_ID")["TEAM_ABBREVIATION"].last()
    totals = (
        pool.loc[pool["season"] == season]
        .groupby("TEAM_ID")
        .agg(diff=("diff", "sum"), poss=("poss", "sum"), n=("diff", "size"))
        .reindex(tricodes.index)
        .reset_index()
        .assign(season=season)
    )
    totals["n"] = totals["n"].fillna(0)
    nr_last = pd.Series(_last_season_nr(ratings, totals), index=totals.index)
    prior = _blend(totals["n"], _net_rating(totals["diff"], totals["poss"]), nr_last, k)
    as_of = pool["GAME_DATE"].max().strftime("%Y-%m-%d")
    return dict(zip(tricodes, prior.astype(float), strict=True)), as_of


def _game_meta(games: pd.DataFrame, priors: pd.DataFrame) -> pd.DataFrame:
    """``games`` rows with the label, the neutral flag and ``prior_diff`` (home - away).

    Games lacking either team's prior are dropped.
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
    return meta


def pregame_states(games: pd.DataFrame, priors: pd.DataFrame) -> pd.DataFrame:
    """The opening state (margin 0, full regulation left) of every game with both priors."""
    meta = _game_meta(games, priors)
    return meta.assign(margin=0.0, seconds_remaining=REGULATION_SECONDS)[STATE_COLUMNS]


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

    Returns ``game_id, season, margin, seconds_remaining, neutral, prior_diff, home_won``
    (empty, with those columns, when no event matches a game). The margin (home - away) is
    summed from scoring events of either side — events of any other team are skipped;
    overtime counts down the extra period only.
    """
    meta = _game_meta(games, priors)
    pbp = pbp.assign(gameId=pbp["gameId"].astype(str))
    pbp = pbp.loc[pbp["gameId"].isin(meta["game_id"])]
    if pbp.empty:
        return pd.DataFrame(columns=STATE_COLUMNS)
    events = pd.concat(
        [sort_chronological(game) for _, game in pbp.groupby("gameId", sort=False)],
        ignore_index=True,
    )
    sides = meta.set_index("game_id")
    for_home = events["teamId"] == events["gameId"].map(sides["home_team_id"])
    for_away = events["teamId"] == events["gameId"].map(sides["away_team_id"])
    points = _event_points(events)
    signed = points.where(for_home, 0) - points.where(for_away, 0)
    margin = signed.groupby(events["gameId"]).cumsum()

    scored = (points > 0) & (for_home | for_away)
    clock = _clock_seconds(events.loc[scored, "clock"])
    periods_left = (4 - events.loc[scored, "period"].astype(int)).clip(lower=0)
    scoring_states = pd.DataFrame(
        {
            "game_id": events.loc[scored, "gameId"],
            "margin": margin[scored].astype(float),
            "seconds_remaining": periods_left * PERIOD_SECONDS + clock,
        }
    ).merge(
        meta[["game_id", "season", "neutral", "prior_diff", "home_won"]],
        on="game_id",
        validate="many_to_one",
    )
    opening = meta.loc[meta["game_id"].isin(events["gameId"])].assign(
        margin=0.0, seconds_remaining=REGULATION_SECONDS
    )
    states = pd.concat([opening[STATE_COLUMNS], scoring_states[STATE_COLUMNS]]).sort_values(
        "game_id", kind="stable"
    )
    return states.reset_index(drop=True)


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
    """Raw coefficients plus readable ratios of them.

    ``homeCourtPts = b/a``, ``pointsPerNetRating = c/a`` and ``scale = 1/a`` are **model
    ratios** in margin units, not literal points: they move (``pointsPerNetRating`` between
    about 1.7 and 2.0) with the seasons the model trains on.
    """
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


def clipped_log_loss(y: np.ndarray, p: np.ndarray) -> float:
    """Binary log-loss with ``p`` clipped to [1e-15, 1 - 1e-15].

    ``predict`` saturates to exactly 0 or 1 on late big leads; clipping keeps the loss finite.
    """
    return float(log_loss(y, np.clip(p, _EPS, 1.0 - _EPS), labels=[0, 1]))


def completed_holdout_seasons(db: Database, n: int = HOLDOUT_SEASONS) -> list[str]:
    """The newest ``n`` seasons with a complete regular season (``SEASON_GAMES`` games rows).

    The gate holds these out, so its split moves forward only when a season completes.
    """
    complete = db.query_df(
        "SELECT season FROM games WHERE season_type = 'Regular Season' "
        "GROUP BY season HAVING COUNT(*) >= ? ORDER BY season",
        [SEASON_GAMES],
    )["season"].tolist()
    return complete[-n:] if n > 0 else []


def evaluate_holdout(
    db: Database, held_out: list[str], k: float = PRIOR_GAMES_K
) -> dict[str, float]:
    """Gate metrics on a temporal holdout: ``held_out`` seasons scored, earlier seasons trained.

    The model and the baseline (``models.win_probability``: margin and time only) train on the
    PBP states of the seasons strictly before ``min(held_out)``; seasons after it that are not
    held out are ignored. The pregame check scores every held-out ``games`` row at tip-off
    (margin 0, f = 1) against a constant equal to the training seasons' home-win rate.

    Returns ``{}`` when either side of the split (PBP states or pregame games) is empty, so
    ``gate_passes`` fails and no NaN is produced.
    """
    if not held_out:
        return {}
    box = db.query_df("SELECT * FROM box_scores_team")
    games = db.query_df("SELECT * FROM games")
    priors = pregame_priors(box, k)
    states = build_states(db.query_df("SELECT * FROM play_by_play"), games, priors)
    pregame = pregame_states(games, priors)

    first = min(held_out)
    train = states.loc[states["season"] < first]
    test = states.loc[states["season"].isin(held_out)]
    pregame_train = pregame.loc[pregame["season"] < first]
    pregame_test = pregame.loc[pregame["season"].isin(held_out)]
    if min(len(train), len(test), len(pregame_train), len(pregame_test)) == 0:
        return {}

    y_test = test["home_won"].astype(int).to_numpy()
    model = fit(train)
    p_test = predict(model, test)

    minutes = {"minutes_remaining": lambda frame: frame["seconds_remaining"] / 60.0}
    baseline = train_win_probability(train.assign(**minutes))
    p_baseline = predict_wp_frame(baseline, test.assign(**minutes))

    y_pregame = pregame_test["home_won"].astype(int).to_numpy()
    home_rate = pregame_train["home_won"].mean()

    return {
        "trainGames": int(train["game_id"].nunique()),
        "holdoutGames": int(test["game_id"].nunique()),
        "holdoutLogLoss": clipped_log_loss(y_test, p_test),
        "baselineLogLoss": clipped_log_loss(y_test, p_baseline),
        "ece": expected_calibration_error(y_test, p_test),
        "pregameLogLoss": clipped_log_loss(y_pregame, predict(model, pregame_test)),
        "constantLogLoss": clipped_log_loss(y_pregame, np.full(len(y_pregame), home_rate)),
    }


def gate_passes(metrics: dict[str, float]) -> bool:
    """Beat the baseline held out, stay calibrated (ECE <= 0.05) and beat a constant pregame.

    Missing metrics (``evaluate_holdout`` had no split) fail.
    """
    if not _GATE_KEYS <= metrics.keys():
        return False
    return bool(
        metrics["holdoutLogLoss"] < metrics["baselineLogLoss"]
        and metrics["ece"] <= MAX_ECE
        and metrics["pregameLogLoss"] < metrics["constantLogLoss"]
    )
