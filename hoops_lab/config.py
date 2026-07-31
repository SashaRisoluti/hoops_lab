"""Central configuration loaded from environment variables.

Single source of truth for runtime settings: every module reads configuration
from here, never from ``os.getenv`` directly. Values come from a local ``.env``
file when present (development) or from real environment variables / Space
Secrets (production on Streamlit Community Cloud). Every setting has a safe default,
so the project also runs with no configuration at all.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # no-op when .env is missing (e.g. on Streamlit Community Cloud)

#: Per-request timeout for nba_api calls, in seconds.
NBA_API_TIMEOUT: int = int(os.getenv("NBA_API_TIMEOUT", "30"))

#: Minimum delay between consecutive nba_api calls, in seconds (rate limit).
NBA_API_DELAY: float = float(os.getenv("NBA_API_DELAY", "0.6"))

#: Path of the local DuckDB database file.
DB_PATH: str = os.getenv("DB_PATH", "data/db/hoops_lab.duckdb")

#: "development" or "production" (the latter disables live-API features).
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

#: Reference team ("my team") for initial tests and scouting comparisons.
#: Swap it by setting REFERENCE_TEAM to any NBA full name as it appears on
#: stats.nba.com (e.g. "Boston Celtics"); it is resolved to a team id at
#: runtime via ``NBAApiClient.team_id_from_name``.
REFERENCE_TEAM: str = os.getenv("REFERENCE_TEAM", "Dallas Mavericks")

#: Seasons preloaded for the public demo (comma-separated in the env var).
DEMO_SEASONS: list[str] = [
    s.strip()
    for s in os.getenv("DEMO_SEASONS", "2021-22,2022-23,2023-24,2024-25,2025-26").split(",")
    if s.strip()
]
