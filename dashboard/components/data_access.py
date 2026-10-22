"""Shared data access for the dashboard (cached database handle + helpers)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from hoops_lab.config import REFERENCE_TEAM
from hoops_lab.storage.database import Database
from hoops_lab.storage.seed import source_dir, source_fingerprint


@st.cache_resource(max_entries=1)
def _database(parquet_fingerprint: str) -> Database:
    """One handle per parquet snapshot: new data opens (and rebuilds) a fresh one."""
    db = Database()
    db.ensure_db_ready()
    return db


def get_database() -> Database:
    """Open the analytical DB, rebuilding it from Parquet if needed (hosted demo).

    Keyed on the parquet fingerprint because Streamlit Cloud applies a data push in
    place without restarting: a plain cached handle would serve last week's data.
    """
    return _database(source_fingerprint(source_dir()))


def team_options(db: Database) -> pd.DataFrame:
    """All NBA teams (team_id, full_name, abbreviation) ordered by name."""
    return db.query_df("SELECT team_id, full_name, abbreviation FROM teams ORDER BY full_name")


def reference_team_index(teams: pd.DataFrame) -> int:
    """Index of the configured reference team in the options (0 if absent)."""
    match = teams.index[teams["full_name"] == REFERENCE_TEAM]
    return int(match[0]) if len(match) else 0
