---
title: Hoops Lab
emoji: 🏀
colorFrom: orange
colorTo: indigo
sdk: streamlit
sdk_version: "1.58.0"
app_file: app.py
pinned: true
license: mit
---

# 🏀 Hoops Lab

Modular NBA data-science framework — **historical analysis**, **pre-game scouting** and **live game intelligence** — built as a professional sports-analytics portfolio project.

**Live demo**: `https://huggingface.co/spaces/<HF_USERNAME>/hoops-lab` *(placeholder — updated once the Space is created)*

## What it does

1. **Historical analysis** — explore seasons, teams, players, trends, traditional and advanced stats through fully dynamic filters (temporal, entity, contextual, statistical with AND/OR logic).
2. **Pre-game scouting** — compare your team with the opponent and surface tactical advantages (shot profiles, lineup efficiency, Matchup Leverage Index).
3. **Live & post-game analysis** — monitor the game in progress, compare live metrics vs historical baselines, raise tactical alerts and generate automated reports.

## Architecture

```
nba_api  →  ingestion  →  Parquet (data/raw)  →  DuckDB (storage)
                                                      ↓
                       features / filters / analytics / live / models
                                                      ↓
                 Streamlit dashboard  ·  FastAPI (Phase 4+)  ·  Python package
```

The framework exposes three independent interfaces:

| Interface | Location | Status |
|---|---|---|
| Streamlit dashboard (main UI) | `dashboard/` | 🚧 Phase 1 |
| FastAPI REST API | `api/` | planned, Phase 4+ |
| Importable Python package | `hoops_lab/` | 🚧 in progress |

## Project structure

```
hoops-lab/
├── app.py                # HuggingFace Spaces entry point (thin wrapper)
├── hoops_lab/            # core package (business logic only)
│   ├── ingestion/        # nba_api client, historical & live downloads
│   ├── storage/          # DuckDB database, schema, migrations, seed
│   ├── features/         # traditional/advanced/possession stats, percentiles
│   ├── filters/          # temporal/entity/contextual/statistical filters + query builder
│   ├── analytics/        # player profile, team identity, scouting, matchups, lineups
│   ├── live/             # live polling, game state, alert engine
│   ├── models/           # win probability, shot quality, lineup recommender (Phase 6)
│   └── reports/          # post-game and scouting reports
├── dashboard/            # Streamlit UI (presentation only)
├── api/                  # FastAPI REST interface (Phase 4+)
├── data/                 # raw / processed / db (see .gitignore policy)
├── notebooks/            # exploratory analysis
└── tests/                # unit / integration / fixtures
```

## Quickstart

```powershell
git clone <repo-url>
cd hoops-lab
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env        # macOS/Linux: cp .env.example .env

# Smoke test — verifies nba_api connectivity (downloads 2023-24 player stats)
python -m hoops_lab.ingestion.nba_api_client

# Run the dashboard
python -m streamlit run dashboard/app.py
```

> Run commands from the repo root and prefer `python -m streamlit ...` so the `hoops_lab` package is always importable.

## Configuration

All settings are environment variables with safe defaults, read exclusively through [`hoops_lab/config.py`](hoops_lab/config.py). Locally they come from `.env`; on HuggingFace Spaces from **Space Secrets**.

| Variable | Default | Purpose |
|---|---|---|
| `NBA_API_TIMEOUT` | `30` | Per-request timeout (seconds) |
| `NBA_API_DELAY` | `0.6` | Minimum delay between nba_api calls (rate limit) |
| `DB_PATH` | `data/db/hoops_lab.duckdb` | DuckDB database file |
| `ENVIRONMENT` | `development` | `production` disables live-API features in the demo |
| `REFERENCE_TEAM` | `Dallas Mavericks` | Your team for tests and scouting comparisons |
| `DEMO_SEASONS` | `2023-24,2024-25,2025-26` | Seasons preloaded for the public demo |

### Changing the reference team

The reference team is **never hard-coded**. To switch from the default (Dallas Mavericks) to any other NBA team:

1. Set `REFERENCE_TEAM` in your `.env` (or as a Space Secret) to the team's full name as it appears on stats.nba.com — e.g. `REFERENCE_TEAM=Boston Celtics`.
2. Done — the name is resolved to the official team id at runtime by `NBAApiClient.team_id_from_name()`.

## Data strategy (public demo)

- Last **3 NBA regular seasons** (2023-24 → 2025-26) preloaded.
- League-wide player box scores and advanced stats; shot charts and play-by-play for a representative sample of games.
- Pre-computed Parquet files in `data/processed/` are versioned in the repo (kept under ~500 MB); the DuckDB file is **rebuilt from Parquet at startup** (`ensure_db_ready()`) because HF Spaces has an ephemeral filesystem.

## Roadmap

- [x] Phase 0 — project scaffold, rate-limited nba_api client
- [x] Phase 1 — Historical dashboard (ingestion, DuckDB, filters, stats table, percentile histogram)
- [x] Phase 2 — Advanced player analytics (player cards, percentile radar, on/off)
- [ ] Phase 3 — Team identity & opponent scouting (Four Factors, Matchup Leverage Index)
- [ ] Phase 4 — Lineup & possession analytics
- [ ] Phase 5 — Live command center (polling, live vs historical, tactical alerts)
- [ ] Phase 6 — Predictive models (win probability, shot quality, lineup recommender) & auto reports

## Testing

```powershell
pytest
```

Unit tests never hit the network; every advanced-stat formula is validated against known reference values.

## Deployment (HuggingFace Spaces)

- Root [`app.py`](app.py) launches the Streamlit dashboard on port 7860 (HF standard).
- `requirements.txt` (flat deps) and `packages.txt` (apt deps) live at the repo root as HF expects.
- [`.github/workflows/sync_to_hf.yml`](.github/workflows/sync_to_hf.yml) force-pushes `main` to the Space on every push. Setup: create the Space, add `HF_TOKEN` as a GitHub Actions secret, replace `<HF_USERNAME>` in the workflow.

## License

[MIT](LICENSE)
