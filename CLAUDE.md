# CLAUDE.md — hoops-lab

Modular NBA data-science framework (professional portfolio project).
Full product spec: `../idee_dashboard_basket_data_science.md` · build plan: `../prompt_claude_code_basketball_framework.md` (both in Italian, outside the repo).

## Language

Code, docstrings, UI and documentation: **English**. Conversation with the user: Italian.

## Phase discipline

Develop in phases (1 → 6, see README roadmap). Never advance to the next phase without the current one working and explicit user confirmation.

## Architecture rules

- Business logic ONLY in `hoops_lab/`; `dashboard/` is presentation-only (Streamlit), `api/` is interface-only (FastAPI, Phase 4+).
- MVP stack: nba_api + pandas/polars + DuckDB + Streamlit + Plotly. The advanced stack (FastAPI/PostgreSQL/Redis/Celery) is added incrementally from Phase 4 — never a rewrite.
- Environment variables are read ONLY via `hoops_lab/config.py` (loads `.env`, safe defaults everywhere). The reference team is configurable via `REFERENCE_TEAM` — never hard-code a team.

## Code quality

- Type hints everywhere; Pydantic v2 models for all external inputs (API payloads, user filters).
- Docstring on every public function (description, params, returns).
- pytest unit tests for every advanced-stat computation and for the query builder. Validate stat formulas against known reference values (e.g. Basketball-Reference). Unit tests never hit the network.

## nba_api operational notes

- Historical data: `from nba_api.stats.endpoints import ...`; live data: `from nba_api.live.nba.endpoints import scoreboard, boxscore, playbyplay`.
- ALL remote calls go through `NBAApiClient` (`hoops_lab/ingestion/nba_api_client.py`): ≥ 0.6 s delay between calls, 30 s timeout, retries with logging. Never instantiate endpoints directly elsewhere.
- Endpoint results: `.get_data_frames()[0]` → pandas DataFrame.

## Data rules

- DuckDB for OLAP aggregations; Parquet as intermediate storage (`data/raw` → `data/processed`).
- Percentiles are ALWAYS computed against the filtered population, never the full universe; cache keyed by a hash of the filter dict (table `player_percentiles`).
- Every analysis enforces minimum-sample filters (minutes, games, possessions).
- HF Spaces has an ephemeral filesystem: the DuckDB file is rebuilt from versioned Parquet at startup (`ensure_db_ready()` in `hoops_lab/storage/database.py`).

## Commands

- Dashboard: `python -m streamlit run dashboard/app.py` (from repo root)
- nba_api smoke test: `python -m hoops_lab.ingestion.nba_api_client`
- Tests: `pytest`
- Lint/format: `ruff check --fix . ; ruff format .`
