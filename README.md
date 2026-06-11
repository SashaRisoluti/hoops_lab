---
title: Hoops Lab
emoji: 🏀
colorFrom: red
colorTo: indigo
sdk: streamlit
sdk_version: "1.58.0"
app_file: dashboard/app.py
pinned: true
license: mit
---

# 🏀 Hoops Lab

Modular NBA data-science framework — **historical analysis**, **pre-game scouting** and **live game intelligence** — built as a professional sports-analytics portfolio project.

**Live demo**: [huggingface.co/spaces/srisoluti/hoops-lab](https://huggingface.co/spaces/srisoluti/hoops-lab)

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
| `DEMO_SEASONS` | `2021-22,...,2025-26` | Seasons preloaded for the public demo |

### Changing the reference team

The reference team is **never hard-coded**. To switch from the default (Dallas Mavericks) to any other NBA team:

1. Set `REFERENCE_TEAM` in your `.env` (or as a Space Secret) to the team's full name as it appears on stats.nba.com — e.g. `REFERENCE_TEAM=Boston Celtics`.
2. Done — the name is resolved to the official team id at runtime by `NBAApiClient.team_id_from_name()`.

## Data strategy (public demo)

- Last **5 NBA regular seasons** (2021-22 → 2025-26) preloaded.
- League-wide player box scores and advanced stats; shot charts and play-by-play for a representative sample of games.
- Pre-computed Parquet files in `data/processed/` are versioned in the repo (kept under ~500 MB); the DuckDB file is **rebuilt from Parquet at startup** (`ensure_db_ready()`) because HF Spaces has an ephemeral filesystem.

## Shot Profile Visual Analytics

The Opponent Scouting page hosts a **Shot Archetypes** section built on two
complementary visual layers (Plotly stays in place for the existing
interactive charts):

- **Altair / Vega-Lite** ([`hoops_lab/visuals/altair_charts.py`](hoops_lab/visuals/altair_charts.py)) — declarative,
  report-friendly chart blocks (Four Factors comparison, percentile bars,
  recent form, zone shot profile, cluster distribution, centroid profiles,
  SOM map). Pure functions: DataFrame in, serializable `alt.Chart` out.
- **Matplotlib court visuals** ([`hoops_lab/visuals/`](hoops_lab/visuals/)) — a hand-drawn NBA half
  court in ShotChartDetail coordinates plus shot scatter maps, density and
  efficiency heatmaps (with a `min_attempts` mask) and archetype centroid
  heatmaps, all `st.pyplot`-compatible.

How the analysis works:

1. **All shots of the selected season** (league-wide, ~220k per season) are
   aggregated into **player-season shot-profile vectors**
   ([`hoops_lab/features/shot_spatial_features.py`](hoops_lab/features/shot_spatial_features.py)): zone frequencies and
   FG%, average distance, points per shot, spatial-bin frequencies, shot
   entropy and zone diversity. Individual shots are never clustered.
2. **KMeans** ([`hoops_lab/models/shot_archetypes.py`](hoops_lab/models/shot_archetypes.py)) extracts discrete
   archetypes from the standardized profiles. Each **centroid is the average
   profile of its archetype — not a real player**; the UI translates
   centroids into readable labels, feature drivers, court heatmaps and the
   closest real example players.
3. A **Self-Organizing Map** ([`hoops_lab/models/shot_som.py`](hoops_lab/models/shot_som.py), MiniSom)
   projects the same vectors onto a 2-D grid that preserves similarity —
   a complementary view for continuity, hybrid profiles and outliers.

The results are **descriptive, not predictive** — the models show which shot
diets exist and who shares them; they do not forecast performance or prove
causality. Profiles aggregate per team as well, and the feature builders
accept a multi-season window (`build_team_window_profile`, default 3
seasons, ready for a 5-season extension).

## Roadmap

- [x] Phase 0 — project scaffold, rate-limited nba_api client
- [x] Phase 1 — Historical dashboard (ingestion, DuckDB, filters, stats table, percentile histogram)
- [x] Phase 2 — Advanced player analytics (player cards, percentile radar, on/off)
- [x] Phase 3 — Team identity & opponent scouting (Four Factors, Matchup Leverage Index, shot map)
- [x] Phase 4 — Lineup & possession analytics (lineup explorer, exact combinations, possession parser)
- [x] Phase 5 — Live command center (replay simulation + live polling, live vs historical, tactical alerts)
- [x] Phase 6 — Predictive models (win probability, shot quality, lineup recommender, run detector) & auto post-game reports

## Testing

```powershell
pytest
```

Unit tests never hit the network; every advanced-stat formula is validated against known reference values.

## Deployment (HuggingFace Spaces)

- With `sdk: streamlit`, the Space runs `streamlit run` itself on `app_file: dashboard/app.py` (the root [`app.py`](app.py) is a local-convenience launcher only).
- `requirements.txt` (flat deps) and `packages.txt` (apt deps) live at the repo root as HF expects.
- [`.github/workflows/sync_to_hf.yml`](.github/workflows/sync_to_hf.yml) force-pushes `main` to the Space on every push. Setup: add a write-scoped `HF_TOKEN` as a GitHub Actions secret.
- The Space rebuilds the DuckDB at boot from the versioned demo parquet in `data/processed/` (set `ENVIRONMENT=production` as a Space variable to disable live-API features).

## License

[MIT](LICENSE)
