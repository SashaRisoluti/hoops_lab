# 🏀 Hoops Lab

Modular NBA data-science framework — **historical analysis**, **pre-game scouting** and **live game intelligence** — built as a professional sports-analytics portfolio project.

| | |
|---|---|
| **Website** | [hoops-lab.vercel.app](https://hoops-lab.vercel.app/) — statically generated, real data, no cold start |
| **Live dashboard** | [hoopslab.streamlit.app](https://hoopslab.streamlit.app/) — the full interactive tool (sleeps when idle) |

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
        Streamlit dashboard  ·  static website (web/)  ·  Python package
```

The framework exposes four independent interfaces over one analytics engine:

| Interface | Location | Status |
|---|---|---|
| Importable Python package | `hoops_lab/` | ✅ all 6 phases complete |
| Streamlit dashboard (full tool) | `dashboard/` | ✅ 9 pages |
| Public website (Next.js, static) | `web/` | ✅ live |
| FastAPI REST API | `api/` | stub, not started |

## Project structure

```
hoops-lab/
├── app.py                # local launcher (deployments use dashboard/app.py)
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
├── web/                  # Next.js public website (static, generated data)
├── scripts/              # CLI utilities incl. the web data export
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

All settings are environment variables with safe defaults, read exclusively through [`hoops_lab/config.py`](hoops_lab/config.py). Locally they come from `.env`; in the hosted demo from the platform's secrets store.

| Variable | Default | Purpose |
|---|---|---|
| `NBA_API_TIMEOUT` | `30` | Per-request timeout (seconds) |
| `NBA_API_DELAY` | `0.6` | Minimum delay between nba_api calls (rate limit) |
| `DB_PATH` | `data/db/hoops_lab.duckdb` | DuckDB database file |
| `ENVIRONMENT` | `development` | `production` disables live-API features in the demo |
| `REFERENCE_TEAM` | `Dallas Mavericks` | Your team for tests and scouting comparisons |
| `DEMO_SEASONS` | `2021-22,...,2026-27` | Seasons preloaded for the public demo; the newest is the one `refresh_season.py` refreshes |
| `FEATURED_MIN_TEAM_GAMES` | `10` | Games every team needs before the newest season becomes the default view |

### Changing the reference team

The reference team is **never hard-coded**. To switch from the default (Dallas Mavericks) to any other NBA team:

1. Set `REFERENCE_TEAM` in your `.env` (or the host's secrets store) to the team's full name as it appears on stats.nba.com — e.g. `REFERENCE_TEAM=Boston Celtics`.
2. Done — the name is resolved to the official team id at runtime by `NBAApiClient.team_id_from_name()`.

## Data strategy (public demo)

- Every regular season in `DEMO_SEASONS` (2021-22 onwards) preloaded; the in-progress season is refreshed weekly (see "Refreshing the current season"). Until every team has played `FEATURED_MIN_TEAM_GAMES` games, the previous season stays the default view.
- League-wide player box scores and advanced stats; shot charts and play-by-play for a representative sample of games.
- Pre-computed Parquet files in `data/processed/` are versioned in the repo with Git LFS (~30 MB); the DuckDB file is **rebuilt from Parquet at startup** (`ensure_db_ready()`) because the hosting filesystem is ephemeral.

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

## Deployment

Two surfaces deploy from this repo, both on a push to `main`.

### Website — Vercel

The Next.js app in [`web/`](web/) is statically generated from JSON exported by
[`scripts/export_web_data.py`](scripts/export_web_data.py), so it loads instantly and needs no
backend. Vercel project setting: **Root Directory `web`**; framework auto-detects; no environment
variables.

Colours are not written by hand — `web/tokens.json` is generated from
[`dashboard/components/theme.py`](dashboard/components/theme.py) and a design gate fails if the
two ever drift apart.

### Dashboard — Streamlit Community Cloud

- Main file path `dashboard/app.py`. The root [`app.py`](app.py) is a local launcher only;
  pointing a host at it would spawn a nested server the host never sees.
- `requirements.txt` (flat deps) and `packages.txt` (apt deps) live at the repo root, where
  Streamlit Cloud looks for them.
- DuckDB is rebuilt at boot from the versioned demo parquet in `data/processed/`, because the
  hosting filesystem is ephemeral. Set `ENVIRONMENT=production` to disable live-API features.
- The free tier sleeps when idle, so the first visit after a quiet period takes ~30s to wake.

### Refreshing the current season

One command, run weekly from a machine that can reach stats.nba.com (with the local
dashboard stopped, since it holds the DuckDB file):

```powershell
python scripts/refresh_season.py          # download, rebuild, re-export; check locally
python scripts/refresh_season.py --push   # same, then commit + push -> both hosts redeploy
```

It downloads the newest season in `DEMO_SEASONS` (league data, per-team lineups and shot
charts, a play-by-play sample), copies it into `data/processed/`, rebuilds DuckDB from exactly
what ships, and re-exports `web/public/data/`. A full run makes ~140 throttled API calls (a few
minutes). Weekly is deliberate: every refresh adds a new version of the season's LFS parquet.

## License

[MIT](LICENSE)
