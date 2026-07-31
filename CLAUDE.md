# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Modular NBA data-science framework (portfolio project). All 6 roadmap phases are complete (see README); deployed as a Streamlit dashboard (Streamlit Community Cloud) and a static Next.js site (Vercel, from `web/`). Original product spec: `../idee_dashboard_basket_data_science.md` and `../prompt_claude_code_basketball_framework.md` (Italian, outside the repo).

Code, docstrings, UI and documentation are in **English**; conversation with the user in **Italian**.

## Commands

Use the project venv: `.venv\Scripts\python.exe` (Windows). Run everything from the repo root — relative data paths and `python -m` imports depend on it.

```powershell
# Tests (unit = offline; integration tests need the local DB, else they skip)
python -m pytest tests -q
python -m pytest tests/unit/test_possession.py::test_and_one_stays_one_possession -q

# Lint / format (config in pyproject.toml, line length 100)
ruff check --fix . ; ruff format .

# Dashboard (python -m keeps the repo root importable)
python -m streamlit run dashboard/app.py

# Data pipeline — order matters:
python -m hoops_lab.ingestion.nba_api_client    # 1. connectivity smoke test
python -m hoops_lab.ingestion.historical        # 2. download demo bundle -> data/raw/*.parquet
python -m hoops_lab.storage.seed                # 3. (re)build DuckDB from parquet
python -m hoops_lab.features.possession         # 4. segment PBP into the possessions table

# Extend the demo bundle with extra seasons (league data, per-team lineups/shots, PBP sample)
python scripts/extend_seasons.py --seasons 2021-22 2022-23 [--skip-pbp]
```

## Development workflow

- **TDD is the default**: write the failing test first (exact hand-computed expected values for stat formulas), then implement. Unit tests never hit the network — mock `NBAApiClient` or register pandas frames into an in-memory `Database(path=":memory:")`.
- Integration tests run against the real DB and include **quality gates** (possession score-reconstruction invariant, shot-model log-loss vs baseline on a temporal holdout, WP AUC on held-out games) plus Streamlit **AppTests** that execute real pages. They `skipif` when `data/db/hoops_lab.duckdb` is missing.
- After UI changes, verify the dashboard actually boots (AppTest or a headless `streamlit run` + HTTP check), not just pytest.
- **Design gates** (`tests/unit/test_design_gates.py`) are permanent lint-as-test rules: no hex literals in `dashboard/` outside `theme.py`, `hoops_lab/visuals` palette mirrors theme tokens, `.streamlit/config.toml` matches tokens, legacy names stay dead. Never weaken them to make a change pass — fix the change.

## Architecture

Data flow: `nba_api → data/raw/*.parquet → DuckDB (data/db/hoops_lab.duckdb) → hoops_lab analytics → Streamlit pages`.

- **Layering**: business logic ONLY in `hoops_lab/`; `dashboard/` is presentation-only; `api/` is a FastAPI stub for later. Env vars are read ONLY via `hoops_lab/config.py` (safe defaults; `.env` optional). The reference team is `REFERENCE_TEAM` — never hard-code a team.
- **Ingestion** (`hoops_lab/ingestion/`): ALL remote calls go through `NBAApiClient` (≥0.6s throttle, 30s timeout, retries). League-wide datasets are one call per season; **lineups and shot charts are downloaded per team** (the league lineup endpoint is capped at 2000 rows server-side; shot files are named `shot_chart_{team_id}_{season}.parquet` so teams coexist). The PBP sample is built with `sample_game_ids_per_team`.
- **Storage** (`hoops_lab/storage/`): SQL migrations own the empty structural tables; the seeder creates data tables straight from parquet (schema inferred, `season` extracted from the filename) and derives `teams`/`players`/`seasons`/`games` plus the `player_season_full` VIEW (base LEFT JOIN advanced — the base every filter query targets). `ensure_db_ready()` rebuilds everything from parquet (the hosting filesystem is ephemeral) and auto-heals older DBs.
- **Filter engine** (`hoops_lab/filters/`): `QueryRequest` → parameterized SQL. Injection guard is three-layered (whitelisted base-table registry, regex-validated quoted identifiers, `?` params). Window operators (`top_n`, `percentile_above/below`, `last_n_games`) compile to `QUALIFY`, which DuckDB evaluates **after** WHERE — that is what guarantees the project's core rule: percentiles always refer to the filtered population, never the full universe.
- **Possession parser** (`hoops_lab/features/possession.py`): state machine over PBPv3 events; points come from offense-team score deltas, so totals are self-validating (the invariant test reconstructs every final score). Events must be re-sorted chronologically (`sort_chronological`) — raw feeds contain out-of-order late-inserted rows.
- **Live pipeline** (`hoops_lab/live/`): one path for replay and live — events → `GameState` (re-segments possessions with the same historical parser, so live PPP/pace are comparable to baselines by construction) → KPIs → alerts. The live feed is adapted to the stats-format contract by `ingestion/live.adapt_live_actions` (lowercase action types, FT `MISS` marker, coordinate passthrough); it is unit-tested but not yet verified against a real live game.
- **Models** (`hoops_lab/models/`): interpretable by design (logistic regressions, shrinkage). Pages train them on demand **excluding the selected game** (no leakage). PER/BPM/VORP are deliberately NOT re-implemented — endpoint values in `advanced_player_stats` are used instead.
- Dashboard pages bootstrap `sys.path` from `__file__` and share `dashboard/components/data_access.py` (cached `get_database()`, team selectors).

## Data gotchas (learned the hard way)

- PBPv3 rebound `subType` is mostly "Unknown": offensive vs defensive is inferred by comparing the rebound's `teamId` with the last missing team.
- Neutral-site games (NBA Cup knockout, Mexico City, Paris) have BOTH team rows in `@` MATCHUP format; the games derivation keeps them flagged `neutral_site` with the lower TEAM_ID as nominal home.
- The assisted flag does not exist in ShotChartDetail — it is recovered from PBP descriptions (`"... (Irving 4 AST)"`) joined on `GAME_EVENT_ID == actionNumber`, so coverage follows the PBP sample.
- DuckDB forbids mixed read-only/read-write opens of the same file within one process: integration tests must use the default write-mode `Database()` because AppTests keep a cached write connection open.
- Computed stat columns carry the `_CALC` suffix to distinguish them from endpoint-provided values (and to allow cross-validation against them).

## Conventions

- Type hints everywhere; Pydantic v2 for external inputs (download requests, filters, alerts); docstrings on public functions.
- Stat functions take a DataFrame and return an enriched **copy** (never mutate); division by zero yields NaN, never inf.
- Minimum-sample filters (minutes, games, possessions) are mandatory in every analysis surface.

## Repo environment cautions

- **OneDrive sync conflicts** create `*-MLNKSO-NW1DRNQ.*` duplicates of source files and of `.git`
  internals (`HEAD`, `index`, `refs/heads/main`). Duplicate pages appear in the Streamlit nav and
  pytest collects duplicate tests. If `git log` fails or conflict copies appear, stop and surface
  it to the user — never resolve `.git` conflict copies silently.
- `requirements.txt` mirrors `[project.dependencies]` in `pyproject.toml` by hand (Streamlit
  Community Cloud needs the flat file) — update both together.
- Session continuity: resume point in `docs/superpowers/RESUME.md`; SDD task ledger in
  `.superpowers/sdd/progress.md` (gitignored).
