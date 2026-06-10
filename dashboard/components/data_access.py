"""Shared data access for the dashboard (cached database handle)."""

from __future__ import annotations

import streamlit as st

from hoops_lab.storage.database import Database


@st.cache_resource
def get_database() -> Database:
    """Open the analytical DB, rebuilding it from Parquet if needed (HF Spaces)."""
    db = Database()
    db.ensure_db_ready()
    return db
