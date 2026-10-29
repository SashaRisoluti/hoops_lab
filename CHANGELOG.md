## README quickstart for anyone cloning the repo (2026-10-29)

- The Quickstart is rewritten for anyone running their own copy. It covers Windows and
  macOS/Linux:
  1. clone with Git LFS, so every season arrives with the clone;
  2. set up;
  3. run the dashboard;
  4. refresh the current season by hand;
  5. refresh it every night (Task Scheduler or cron).
- `schedule_refresh.ps1 -LocalOnly` refreshes a clone's data and dashboard without
  committing or pushing, for people without write access. Pushing stays the default for the
  repo owner.

## Possession points from events; daily refresh (2026-10-29)

- The weekly refresh of 2026-10-26 was stopped by its safety gate: the score-reconstruction
  test found HOU @ SAS (0022600009) off by 7. **Root cause:** scorer corrections, entered a
  quarter later, carry the scoreboard of their insertion time. Once sorted back to their real
  time, that snapshot runs backwards, so score deltas double count. Possession points now come
  from the scoring events: made shots at `shotValue`, made free throws. Summed events match the
  box score on all 882 sampled team-games. Reconstruction improves in every season, and
  segmentation is unchanged.
- `schedule_refresh.ps1 -Daily`: refresh every morning after the NBA night. The task is renamed
  "hoops-lab data refresh"; registering it removes the legacy "hoops-lab weekly refresh". The
  README documents the Git LFS cost of a daily cadence.
- **Shared connection race (hosted app).** Overview on 2026-27 crashed with "'NoneType' object
  is not subscriptable", and the log also showed `KeyError: 'game_id'`. The dashboard shares
  one cached `Database` between all sessions, each running in its own thread, and a DuckDB
  connection is not thread-safe. Locally, 170 of 800 threaded queries returned None. Every
  use of the connection now holds a re-entrant lock. `shot_context` registers its selection
  and queries it atomically, because that registered name is shared by every session. All 10
  pages were checked with 2026-27 selected: they pass locally and on Streamlit Cloud.

## Hosted-app hardening after the 2026-10-22 outage

- **Outage:** Streamlit Cloud (Python 3.14) resolved `duckdb>=1.0` to DuckDB 2.0.0. Its
  connections refuse new work while an `execute()` result is pending, so the boot-time seed
  died with `ResourceInUseException`. Every local test was green on 1.5.5.
  `requirements.txt` is now an exact lock of the tested set (`pyproject.toml` keeps the
  floors).
- The aborted 2.0 boot left a database file 1.5 cannot read. `Database.connect()` now
  replaces a DuckDB file it cannot open (the file is a cache of the parquet). Lock conflicts
  and read-only opens still raise.
- **Data refreshes now reach the hosted dashboard.** A data push updates the hosted repo in
  place, without a restart. The seed stores a parquet fingerprint (`seed_source`):
  `ensure_db_ready()` reseeds when it no longer matches, and `get_database()` is cached per
  fingerprint.
- The default seed source is the versioned `data/processed`. `data/raw` is only a staging
  area: after a refresh on a new PC it holds the current season alone.
- Verified on Streamlit Cloud: neither NBA source is reachable from there. `cdn.nba.com`
  answers 403 and `stats.nba.com` times out. Hosted live mode degrades to a warning; live data
  works locally.

## Live fallback + auto-refresh, unattended refresh, new-PC setup (2026-10-22)

- Live mode tries the NBA live CDN first and falls back to stats.nba.com (ScoreboardV3 +
  PlayByPlayV3) with a 10 s, single-attempt client, so a blocked host cannot hang the page.
  Verified on two final games: parsed scores match the scoreboard exactly.
- Live mode auto-refreshes with `st.fragment(run_every=LIVE_REFRESH_SECONDS)` (default 30);
  replay is unchanged. The picker lists in-progress then finished games with their status
  text; a caption shows the source in use and the last update (ET).
- `LivePoller.events()` returns stats-contract events in chronological order whatever the
  source (replaces `play_by_play()`).
- `featured_season`: a team that has not played yet now counts as 0 games, so "every team"
  is enforced (found in pre-push review).
- `refresh_season.py --push` is safe unattended: main only, rebases before downloading and
  before pushing, full test suite as a gate, commits only the data paths, timestamped log.
- `scripts/schedule_refresh.ps1` (weekly per-user Scheduled Task) and
  `scripts/setup_machine.ps1` (one-command bootstrap of a fresh clone: LFS data, venv, deps,
  DuckDB — no historical re-download).

## Season 2026-27 + weekly refresh + live fixes (2026-10-22)

- 2026-27 added to `DEMO_SEASONS` and ingested (the season opened 2026-10-20).
- **Featured season**: `hoops_lab.analytics.seasons.featured_season` is the newest season in
  which every team has played `FEATURED_MIN_TEAM_GAMES` (default 10) games, else the previous
  one. It drives the dashboard's default season, the website headline season (`index.json`
  key renamed `latestSeason` -> `featuredSeason`, since it is no longer always the newest)
  and the live-mode baselines. 2026-27 stays selectable everywhere from day one.
- `scripts/refresh_season.py [--push]`: one-command weekly refresh (download -> publish to
  `data/processed` -> reseed from what ships -> web export -> optional commit + push).
- Fix: `LivePoller` shared one throttle clock between the scoreboard and play-by-play, so
  the scoreboard call made first on every rerun starved the play-by-play — a live game froze
  on its first snapshot. Each feed now has its own clock; an empty scoreboard no longer
  bypasses the throttle either.
- Fix: `temporal_split` trained on every season other than the test one, including later
  ones; it now trains strictly on earlier seasons, as its docstring always claimed.
- Web home: the seasons range is derived from the data instead of hard-coded.
- `numpy` declared as a direct dependency (it was imported directly but only arrived via
  pandas). "Space Secrets" wording from the HuggingFace era replaced.

## Deployment consolidated: Vercel + Streamlit Cloud (2026-07-31)

- The website is live at <https://hoops-lab.vercel.app/> (Next.js, static, root directory
  `web/`); the dashboard at <https://hoopslab.streamlit.app/>.
- HuggingFace Spaces retired. Removed `.github/workflows/sync_to_hf.yml` — it would have
  failed on every push once the Space was deleted — and the HF YAML frontmatter from the
  README. The `HF_TOKEN` secret is no longer used.
- Reworded, not removed, the comments explaining `ensure_db_ready()`: the ephemeral-filesystem
  rationale still applies on Streamlit Community Cloud, so the mechanism stays.
- Root `app.py` now defaults to Streamlit's port 8501 instead of the HF-specific 7860, and its
  docstring warns that pointing a host at it spawns a nested server.
- README refreshed: both live links, four-interface table (the dashboard was still marked
  "Phase 1"), `web/` and `scripts/` added to the structure, and a rewritten deployment section.

## Web shell Phase 1 — Task 6: About page (2026-07-31)

- Engineering story: the five-stage pipeline (ingestion, storage, possession parser,
  filter engine, models) and how correctness is enforced — score-reconstruction
  invariants, model quality gates, and the design-token drift gate.
- Every figure is derived, never written down: `index.json` now carries `shots`,
  `possessions`, and a `project` block counting test functions and Python modules
  straight from the source tree (1,091,329 shots, 77,299 possessions, 305 tests,
  55 modules).
- JSON-LD `Person` and `Dataset` graphs; LinkedIn and dashboard links.
- `opengraph-image.tsx` generates a real 1200x630 card at build time from the token
  palette and live counts, so shared links preview with actual numbers rather than the
  blank card the reference site produces.

## Web shell Phase 1 — Task 5: home page (2026-07-31)

- Hero renders real 2025-26 data: headline counts, league leaders with the
  minimum-sample thresholds shown, and the five best teams by net rating.
- New signature visual `CourtZones`: a bespoke SVG half court in real court units,
  each zone shaded by points per shot against the league average. Backed by a new
  `shot-zones/{season}.json` export (219,131 attempts aggregated to six zones).
- **Bug fixed in the zone export**: valuing a zone by its maximum shot type let 8
  mislabelled 3PT rows out of 22,025 reprice every mid-range jumper at three points,
  inflating its points per shot from 0.83 to 1.25. Each shot is now valued on its own
  row; a regression test covers a contaminated zone.
- **Design-system fix in `StatTile`**: the team accent no longer colours the value.
  Tinting a value by franchise made Detroit's +8.4 red and Boston's +8.3 green, which
  contradicts the fixed green/yellow/red data language. The accent is now a marker
  beside the label.
- Verified in a real browser at 1440px and 360px: no horizontal scroll, no JS errors.

## Web shell Phase 1 — Task 4: Next.js skeleton (2026-07-31)

- New `web/`: Next.js 15 App Router + React 19 + Tailwind 3.4, all routes statically
  generated. First Load JS 103 kB, under the 150 kB budget.
- `tailwind.config.ts` derives every colour from the generated `web/tokens.json`, so the
  Streamlit theme is the single source of truth for both surfaces. Verified end to end:
  the Python token values appear in the compiled CSS bundle.
- `AppShell` (sticky topbar, nav collapsing at 980px with `aria-expanded`/`aria-controls`),
  `StatTile` and `PageHeader` ported from their Streamlit counterparts, plus a skip link
  and a visible focus ring.
- `app/robots.ts` and `app/sitemap.ts`; per-route metadata with Open Graph and Twitter
  cards — the reference site ships none of this.
- New design gate `test_no_hex_literals_in_the_web_app` mirrors the dashboard rule, so
  the web app cannot hardcode a colour outside the generated tokens.

## Web shell Phase 1 — Task 3: dataset export (2026-07-30)

- `scripts/export_web_data.py` now writes `web/public/data/`: `index.json` (seasons, 30
  teams with accents, headline counts), plus `leaders/{season}.json` and
  `teams/{season}.json` for all five demo seasons. 11 files, 87.6 KB total.
- Leaderboards apply and publish the mandatory minimum sample (`GP >= 20`,
  `MIN >= 15.0`); team ratings reuse `analytics.team_identity.league_ratings`, so no
  statistic is recomputed for the web app.
- Integration tests assert the export stays under a 2 MB budget and that exported
  leaders match a direct DuckDB query exactly.

## Web shell Phase 1 — Task 2: token bridge (2026-07-30)

- `scripts/export_web_data.py --tokens-only` generates `web/tokens.json` from
  `theme.TOKENS` and `theme.TEAM_ACCENTS_READABLE`. Deterministic output (no timestamp)
  so the artifact only changes when the tokens do.
- New design gate `test_web_tokens_artifact_matches_theme` fails when a token is edited
  without re-exporting, so Streamlit and the web app cannot drift apart.
- Fixed the long-standing AppTest flake: `test_chart_components_colors` ran against
  Streamlit's 3s default script timeout while the apps need up to ~16s to import pandas
  and plotly on a loaded machine. Timeout raised; assertions unchanged.
- `.gitignore` covers `web/node_modules/`, `.next/`, `out/`, `.vercel/`.

## Web shell Phase 1 — Task 1: readable team accents (2026-07-30)

- New `hoops_lab/visuals/team_colors.py`: WCAG contrast helpers, minimal-lift
  `ensure_contrast()`, and `resolve_pair()` for franchises that share a hex.
- `theme.TEAM_ACCENTS_READABLE` guarantees WCAG 3:1 against `BG_PAGE`; the team rail and the
  app shell now paint it. Only SAC changes (`#5A2D81` → `#7f3fb6`, contrast 1.99 → 3.08) —
  the other 29 official colours are preserved exactly.
- A fixed 52% lightness floor was measured and rejected: it would have altered 18 accents that
  already pass, turning Boston green neon.

## Worldcup26 UI restyle — Phase B (2026-07-24)

- All 9 pages migrated to PageHeader; searchable pickers (player, opponent, games) via SearchSelect.
- Every Plotly surface on the shared `plotly_layout()` template; semantic weak/mid/good scales
  replace RdYlGn; `hoops_lab/visuals` palette mirror synced to the Worldcup26 tokens.
- Live KPI strip renders StatTiles; NaN guards on StatTile delta/percentile.
- Legacy aliases (`ORANGE/BLUE/RED/...`), `kpi_card` deleted; small tile renamed `mini_tile`.
- Permanent gates: no-hex-outside-theme, visuals-mirror sync, config.toml/token sync.

## Worldcup26 UI restyle — Phase A (2026-07-24)

- Semantic design tokens (`COLOR_GOOD/MID/WEAK/PRIMARY`) on the Worldcup26 navy palette;
  legacy `ORANGE/BLUE/RED` names alias the new values until Phase B.
- Inter / Inter Tight typography; primary-blue nav and team-rail chrome.
- New components: StatTile, PageHeader, SearchSelect, InfoTooltip.
- Overview migrated to StatTile + PageHeader; shared Plotly template.
