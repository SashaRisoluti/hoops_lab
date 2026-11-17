"""Reliability diagram of the /live game win-probability model on the last complete season.

The model (``hoops_lab.models.game_win_probability``) is trained on every season strictly
before the newest complete regular season and scored on that season's PBP states (tip-off
plus every scoring event), the same temporal split as the export gate. States are binned
into deciles of predicted home-win probability (equal-count bins); each point is a bin's
mean prediction against its observed home-win rate. The Brier score is in the title.

States of one game are correlated, so bins are not independent samples: read the diagram
as calibration, not as a significance test.

Run from the repo root::

    python scripts/calibration_plot.py            # -> docs/img/calibration.png
    python scripts/calibration_plot.py --out other.png
"""

from __future__ import annotations

import argparse
import sys
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

from dashboard.components.theme import TOKENS  # noqa: E402
from hoops_lab.models.game_win_probability import (  # noqa: E402
    build_states,
    completed_holdout_seasons,
    expected_calibration_error,
    fit,
    predict,
    pregame_priors,
)
from hoops_lab.storage.database import Database  # noqa: E402

OUT_PATH = "docs/img/calibration.png"
BINS = 10


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


def holdout_predictions(db: Database) -> tuple[str, np.ndarray, np.ndarray, int, int]:
    """Season, outcomes and predictions of the last complete season, plus train/test games."""
    seasons = completed_holdout_seasons(db, n=1)
    if not seasons:
        raise SystemExit("no complete regular season in the database")
    season = seasons[0]
    states = build_states(
        db.query_df("SELECT * FROM play_by_play"),
        db.query_df("SELECT * FROM games"),
        pregame_priors(db.query_df("SELECT * FROM box_scores_team")),
    )
    train = states.loc[states["season"] < season]
    test = states.loc[states["season"] == season]
    if train.empty or test.empty:
        raise SystemExit(f"no PBP states to train before or score in {season}")
    y = test["home_won"].astype(int).to_numpy()
    return (
        season,
        y,
        predict(fit(train), test),
        train["game_id"].nunique(),
        test["game_id"].nunique(),
    )


def plot(table: pd.DataFrame, title: str, out: Path) -> None:
    """Draw the reliability diagram (theme tokens, dark card) and save it as PNG."""
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    fig.patch.set_facecolor(TOKENS["bg_card"])
    ax.set_facecolor(TOKENS["bg_card"])
    ax.plot([0, 1], [0, 1], linestyle="--", color=TOKENS["text_faint"], label="Perfect calibration")
    ax.plot(
        table["predicted"],
        table["observed"],
        marker="o",
        color=TOKENS["primary"],
        label="Model (deciles)",
    )
    ax.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Predicted home win probability",
        ylabel="Observed home win rate",
    )
    ax.set_title(title, color=TOKENS["text"], fontsize=10)
    ax.grid(color=TOKENS["grid"], linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color(TOKENS["border"])
    ax.tick_params(colors=TOKENS["text_soft"])
    ax.xaxis.label.set_color(TOKENS["text_soft"])
    ax.yaxis.label.set_color(TOKENS["text_soft"])
    legend = ax.legend(loc="upper left", facecolor=TOKENS["bg_tile"], edgecolor=TOKENS["border"])
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
        season, y, p, train_games, test_games = holdout_predictions(db)
    finally:
        db.close()

    table = reliability_table(y, p)
    brier = brier_score(y, p)
    ece = expected_calibration_error(y, p)
    title = (
        f"Game win probability, {season} held out ({test_games} games, {len(y):,} states)\n"
        f"Brier {brier:.4f} | ECE {ece:.4f} | trained on {train_games} earlier games"
    )
    out = ROOT / args.out
    plot(table, title, out)
    print(table.to_string(float_format="%.3f"))
    print(f"season={season} brier={brier:.4f} ece={ece:.4f} -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
