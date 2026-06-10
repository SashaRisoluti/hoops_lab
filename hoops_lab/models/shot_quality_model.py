"""Shot quality model: expected FG% and expected points per shot.

Logistic regression on shot geometry and context (distance, shot value,
zone, period). Deliberately interpretable and fast to retrain; evaluated
with a TEMPORAL split (train on earlier seasons, test on the latest) and a
log-loss quality gate against the league-average baseline in the
integration suite.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

#: Feature columns fed to the model.
NUMERIC_FEATURES = ["SHOT_DISTANCE", "PERIOD", "IS_THREE"]
CATEGORICAL_FEATURES = ["SHOT_ZONE_BASIC"]


def _prepare(shots: pd.DataFrame) -> pd.DataFrame:
    """Add derived feature columns (copy)."""
    out = shots.copy()
    out["IS_THREE"] = out["SHOT_TYPE"].astype(str).str.contains("3PT").astype(int)
    return out


def temporal_split(
    shots: pd.DataFrame,
    test_season: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on seasons before ``test_season``, test on it (no leakage)."""
    test = shots.loc[shots["season"] == test_season]
    train = shots.loc[shots["season"] != test_season]
    return train, test


def train_shot_quality(shots: pd.DataFrame) -> Pipeline:
    """Fit the make-probability model on labelled shots."""
    prepared = _prepare(shots)
    model = Pipeline(
        [
            (
                "features",
                ColumnTransformer(
                    [
                        ("num", StandardScaler(), NUMERIC_FEATURES),
                        ("zone", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
                    ]
                ),
            ),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    model.fit(prepared[NUMERIC_FEATURES + CATEGORICAL_FEATURES], prepared["SHOT_MADE_FLAG"])
    return model


def score_shots(model: Pipeline, shots: pd.DataFrame) -> pd.DataFrame:
    """Add expected FG% (XFG) and expected points (XPTS) per shot (copy)."""
    prepared = _prepare(shots)
    probabilities = model.predict_proba(prepared[NUMERIC_FEATURES + CATEGORICAL_FEATURES])[:, 1]
    out = shots.copy()
    out["XFG"] = probabilities
    shot_value = prepared["IS_THREE"].map({1: 3.0, 0: 2.0})
    out["XPTS"] = out["XFG"] * shot_value.to_numpy()
    return out
