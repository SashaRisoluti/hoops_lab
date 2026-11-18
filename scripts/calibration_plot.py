"""Reliability diagram of the /live game win-probability model on the last complete season.

The model (``hoops_lab.models.game_win_probability``) is trained on every season strictly
before the newest complete regular season and scored on that season's PBP states (tip-off
plus every scoring event), the same temporal split as the export gate. Only the whole-season
random games are scored (see :func:`whole_season_game_ids`); training keeps every PBP game.
States are binned into deciles of predicted home-win probability (equal-count bins); each
point is a bin's mean prediction against its observed home-win rate.

Post-hoc calibration is tested without touching the held-out season: a base model is fitted
on the seasons before the calibration season (the one right before the held-out season),
and temperature, Platt and isotonic calibrators are fitted on the calibration season. The
choice uses only the calibration season: 5-fold cross-validation grouped by game, lowest
Brier, and a calibrator is adopted only if it beats no calibration. All curves are then
drawn on the held-out season, with Brier and ECE in the legend.

States of one game are correlated, so bins are not independent samples: read the diagram
as calibration, not as a significance test. The ECE interval is a game-cluster bootstrap.

Run from the repo root::

    python scripts/calibration_plot.py            # -> docs/img/calibration.png
    python scripts/calibration_plot.py --out other.png
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

# Repo root importable regardless of how the script is launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

from dashboard.components.theme import TOKENS  # noqa: E402
from hoops_lab.ingestion.historical import (  # noqa: E402
    PBP_RANDOM_GAMES,
    PBP_RANDOM_SEED,
    random_season_game_ids,
)
from hoops_lab.models.game_win_probability import (  # noqa: E402
    build_states,
    completed_holdout_seasons,
    expected_calibration_error,
    features,
    fit,
    predict,
    pregame_priors,
)
from hoops_lab.storage.database import Database  # noqa: E402
from hoops_lab.storage.seed import PROCESSED_DATA_DIR  # noqa: E402

OUT_PATH = "docs/img/calibration.png"
BINS = 10
CV_FOLDS = 5
CALIBRATORS = ("none", "temperature", "platt", "isotonic")

Calibrator = Callable[[np.ndarray], np.ndarray]


def reliability_table(y: np.ndarray, p: np.ndarray, bins: int = BINS) -> pd.DataFrame:
    """Mean prediction, observed rate and count per equal-count bin of ``p``.

    Ties are broken by order (``rank(method="first")``), so saturated predictions still
    fill every bin instead of collapsing quantile edges.
    """
    frame = pd.DataFrame({"y": np.asarray(y, float), "p": np.asarray(p, float)})
    frame["bin"] = pd.qcut(frame["p"].rank(method="first"), bins, labels=False)
    return (
        frame.groupby("bin")
        .agg(predicted=("p", "mean"), observed=("y", "mean"), n=("y", "size"))
        .reset_index(drop=True)
    )


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    """Mean squared error between predicted probability and the 0/1 outcome."""
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def fit_calibrators(z: np.ndarray, y: np.ndarray) -> dict[str, Calibrator]:
    """Map logit -> probability for each method in ``CALIBRATORS``, fitted on ``(z, y)``.

    ``temperature`` rescales the logit (no intercept, so the home/away symmetry of the model
    survives), ``platt`` adds an intercept, ``isotonic`` is a monotone step function.
    """
    column = np.asarray(z, float).reshape(-1, 1)
    temperature = LogisticRegression(fit_intercept=False, C=np.inf).fit(column, y)
    platt = LogisticRegression(C=np.inf).fit(column, y)
    isotonic = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(column[:, 0], y)
    return {
        "none": lambda x: 1.0 / (1.0 + np.exp(-np.asarray(x, float))),
        "temperature": lambda x: temperature.predict_proba(np.reshape(x, (-1, 1)))[:, 1],
        "platt": lambda x: platt.predict_proba(np.reshape(x, (-1, 1)))[:, 1],
        "isotonic": lambda x: isotonic.predict(np.asarray(x, float)),
    }


def pick_calibrator(cv: pd.DataFrame) -> str:
    """Lowest cross-validated Brier; ``none`` unless another method is strictly lower."""
    best = cv["brier"].idxmin()
    return best if cv.loc[best, "brier"] < cv.loc["none", "brier"] else "none"


def choose_calibrator(
    z: np.ndarray, y: np.ndarray, groups: np.ndarray, folds: int = CV_FOLDS
) -> tuple[str, pd.DataFrame]:
    """Chosen method and its CV table (Brier, ECE), from game-grouped K-fold on ``(z, y)``.

    Out-of-fold predictions only: scoring a calibrator on the states it was fitted on
    rewards overfitting (isotonic reaches ECE 0 that way).
    """
    z, y = np.asarray(z, float), np.asarray(y, int)
    oof = {name: np.zeros(len(y)) for name in CALIBRATORS}
    for train, test in GroupKFold(folds).split(z, y, groups):
        fitted = fit_calibrators(z[train], y[train])
        for name in CALIBRATORS:
            oof[name][test] = fitted[name](z[test])
    cv = pd.DataFrame(
        {
            "brier": [brier_score(y, oof[name]) for name in CALIBRATORS],
            "ece": [expected_calibration_error(y, oof[name]) for name in CALIBRATORS],
        },
        index=list(CALIBRATORS),
    )
    return pick_calibrator(cv), cv


def cluster_bootstrap_ece(
    y: np.ndarray, p: np.ndarray, groups: np.ndarray, n_boot: int = 1000, seed: int = 0
) -> tuple[float, float]:
    """95% interval of the ECE, resampling whole games (states of a game are correlated)."""
    frame = pd.DataFrame({"y": y, "p": p, "g": groups})
    by_game = [game[["y", "p"]].to_numpy(float) for _, game in frame.groupby("g")]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        sample = np.concatenate([by_game[i] for i in rng.integers(0, len(by_game), len(by_game))])
        draws.append(expected_calibration_error(sample[:, 0], sample[:, 1]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def whole_season_game_ids(season: str, processed_dir: Path = PROCESSED_DATA_DIR) -> set[str]:
    """The seeded whole-season random PBP games of ``season``.

    The rest of the PBP sample is each team's last games (the final fortnight), which is not
    representative of the season, so the calibration set and the held-out season use only these.
    """
    team_box = pd.read_parquet(Path(processed_dir) / f"team_box_{season}.parquet")
    return set(random_season_game_ids(team_box, PBP_RANDOM_GAMES, PBP_RANDOM_SEED))


def _logit(model: LogisticRegression, states: pd.DataFrame) -> np.ndarray:
    return model.decision_function(features(states))


def plot(curves: dict[str, tuple[pd.DataFrame, str]], title: str, out: Path) -> None:
    """Draw the reliability curves (label -> (table, style key)) and save them as PNG."""
    styles = {
        "raw": {"color": TOKENS["primary"], "linestyle": "-", "marker": "o", "linewidth": 2},
        "temperature": {"color": TOKENS["good"], "linestyle": "--", "marker": "s"},
        "platt": {"color": TOKENS["mid"], "linestyle": "-.", "marker": "^"},
        "isotonic": {"color": TOKENS["weak"], "linestyle": ":", "marker": "D"},
    }
    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    fig.patch.set_facecolor(TOKENS["bg_card"])
    ax.set_facecolor(TOKENS["bg_card"])
    ax.plot([0, 1], [0, 1], linestyle="--", color=TOKENS["text_faint"], label="Perfect calibration")
    for label, (table, key) in curves.items():
        ax.plot(table["predicted"], table["observed"], markersize=4, label=label, **styles[key])
    ax.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Predicted home win probability",
        ylabel="Observed home win rate",
    )
    ax.set_title(title, color=TOKENS["text"], fontsize=9)
    ax.grid(color=TOKENS["grid"], linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color(TOKENS["border"])
    ax.tick_params(colors=TOKENS["text_soft"])
    ax.xaxis.label.set_color(TOKENS["text_soft"])
    ax.yaxis.label.set_color(TOKENS["text_soft"])
    legend = ax.legend(
        loc="lower right",
        fontsize=7.5,
        facecolor=TOKENS["bg_tile"],
        edgecolor=TOKENS["border"],
    )
    for text in legend.get_texts():
        text.set_color(TOKENS["text"])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=OUT_PATH, help=f"PNG path (default {OUT_PATH})")
    args = parser.parse_args(argv)

    db = Database()
    try:
        db.ensure_db_ready()
        held = completed_holdout_seasons(db, n=1)
        games = db.query_df("SELECT * FROM games")
        states = build_states(
            db.query_df("SELECT * FROM play_by_play"),
            games,
            pregame_priors(db.query_df("SELECT * FROM box_scores_team")),
        )
    finally:
        db.close()
    if not held:
        raise SystemExit("no complete regular season in the database")
    season = held[0]
    earlier = sorted(states.loc[states["season"] < season, "season"].unique())
    if len(earlier) < 2 or not (states["season"] == season).any():
        raise SystemExit(f"need PBP states for {season} and two seasons before it")
    cal_season = earlier[-1]

    train = states.loc[states["season"] < season]
    # Evaluate on the whole-season random games only; training keeps every PBP game.
    test = states.loc[
        (states["season"] == season) & states["game_id"].isin(whole_season_game_ids(season))
    ]
    cal = states.loc[
        (states["season"] == cal_season) & states["game_id"].isin(whole_season_game_ids(cal_season))
    ]
    if test.empty or cal.empty:
        raise SystemExit("no whole-season random PBP games: run scripts/extend_seasons.py")
    y, y_cal, y_train = (frame["home_won"].astype(int).to_numpy() for frame in (test, cal, train))

    # Raw: the shipped recipe, trained on every season before the held-out one.
    raw_model = fit(train)
    p_raw = predict(raw_model, test)
    in_sample_ece = expected_calibration_error(y_train, predict(raw_model, train))
    ece_lo, ece_hi = cluster_bootstrap_ece(y, p_raw, test["game_id"].to_numpy())

    # Calibration: base model before the calibration season, calibrators on it, CV choice.
    base = fit(states.loc[states["season"] < cal_season])
    z_cal, z_test = _logit(base, cal), _logit(base, test)
    chosen, cv = choose_calibrator(z_cal, y_cal, cal["game_id"].to_numpy())
    fitted = fit_calibrators(z_cal, y_cal)

    def legend(name: str, p: np.ndarray) -> str:
        return f"{name}: Brier {brier_score(y, p):.4f} | ECE {expected_calibration_error(y, p):.4f}"

    curves = {legend("Raw (trained < held-out)", p_raw): (reliability_table(y, p_raw), "raw")}
    for name in CALIBRATORS[1:]:
        p = fitted[name](z_test)
        curves[legend(f"{name.capitalize()} (fit on {cal_season})", p)] = (
            reliability_table(y, p),
            name,
        )

    sample = games.loc[games["game_id"].astype(str).isin(test["game_id"])]
    first, last = (
        pd.Timestamp(d).strftime("%Y-%m-%d") for d in sample["game_date"].agg(["min", "max"])
    )
    regular = games.loc[(games["season"] == season) & (games["season_type"] == "Regular Season")]
    season_home = float((regular["home_pts"] > regular["away_pts"]).mean())
    sample_home = float(test.drop_duplicates("game_id")["home_won"].mean())

    title = (
        f"Game win probability, {season} held out: whole-season random sample {first} to {last}\n"
        f"({test['game_id'].nunique()} games, {len(y):,} states; home wins {sample_home:.0%} "
        f"vs {season_home:.0%} full season)\n"
        f"chosen calibrator: {chosen} (5-fold game CV on {cal_season}, lowest Brier)"
    )
    out = ROOT / args.out
    plot(curves, title, out)

    print(f"calibration set {cal_season}, game-grouped {CV_FOLDS}-fold CV:")
    print(cv.to_string(float_format="%.4f"))
    print(f"chosen: {chosen}")
    print(f"held-out {season}: {test['game_id'].nunique()} games, {first} to {last}")
    print(f"home win rate: sample {sample_home:.3f} vs full regular season {season_home:.3f}")
    for label in curves:
        print(f"  {label}")
    print(
        f"raw in-sample ECE {in_sample_ece:.4f}; raw held-out ECE "
        f"{expected_calibration_error(y, p_raw):.4f}, game-cluster bootstrap 95% "
        f"[{ece_lo:.3f}, {ece_hi:.3f}]"
    )
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
