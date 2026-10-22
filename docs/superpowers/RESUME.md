# Session Resume Point

Last updated: 2026-10-22.

## Current state

- **Season 2026-27 (opened 2026-10-20) is ingested**, with a one-command weekly refresh:
  `python scripts/refresh_season.py [--push]`. The default ("featured") season stays 2025-26
  until every team has played `FEATURED_MIN_TEAM_GAMES` (10) games — `featured_season()` in
  `hoops_lab/analytics/seasons.py` drives the dashboard selector, the web headline season
  (`index.json` `featuredSeason`) and the live baselines.
- **Live mode:** `LivePoller` no longer freezes the play-by-play (it shared one throttle clock
  with the scoreboard). Still open: `cdn.nba.com` (nba_api live) is 403-blocked on the corporate
  network, so live mode can only be checked on the hosted app or off-network; a stats-endpoint
  fallback (ScoreboardV3 + PlayByPlayV3, PBPv3 needs no adapter) and `st.fragment(run_every=)`
  auto-refresh are the next live improvements. Streamlit Cloud has no `ENVIRONMENT` secret, so
  live mode is visible there.
- **Deployed 2026-07-31:** website https://hoops-lab.vercel.app/ (Vercel, root `web/`),
  dashboard https://hoopslab.streamlit.app/. HuggingFace Spaces retired. Single branch `main`.
- **Worldcup26 UI restyle (Phase A + B): COMPLETE and merged.** Phase A at `ef4c8fc`, Phase B
  `d278796..bba45af`, resume-point commit `2366992`.
- **2026-07-30: OneDrive corruption recovered.** A PC shutdown mid-session left OneDrive
  renaming `.git/HEAD`, `refs/heads/main` and `index` into `*-MLNKSO-NW1DRNQ` copies, and
  reverting 20 source files to older content while the newest content sat in conflict copies.
  Fully recovered; all 76 conflict copies removed. Verified: 214 unit + 14 integration tests
  green, ruff clean, dashboard boots HTTP 200.
- **The repo moved to `C:\dev\hoops-lab`** on 2026-07-30. The OneDrive folder is retired and
  carries a `_STALE_DO_NOT_USE.md` marker. Corporate TLS breaks `git-lfs`; fixed globally with
  `http.sslCAInfo` pointing at an exported Windows CA bundle.

## Public web shell — Phase 1 shipped (2026-07-31); Phase 2 not started

Specced 2026-07-30, merged to `main` and deployed to Vercel. Phase 2 (`/archetypes` page plus
the deferred `archetypes/{season}.json` export) has not started. The notes below are the
Phase 1 history.

| Doc | Path |
|---|---|
| Design spec | `docs/superpowers/specs/2026-07-30-web-shell-design.md` |
| Phase 1 plan | `docs/superpowers/plans/2026-07-30-web-shell-phase-1.md` |

**Shape:** a statically generated Next.js site in `web/`, deployed to Vercel on a custom domain,
rendering real NBA data exported from DuckDB at build time. Purpose is portfolio-first — it
carries the first impression with zero cold start and links onward to Streamlit for deep work.
`hoops_lab/` stays the single source of truth; no analytics are reimplemented in TypeScript.

**Confirmed decisions:** hybrid shell rather than full migration; Next.js App Router over Astro
and over a Vite SPA (per-route SEO/OG is mandatory and is the reference's fatal flaw); bespoke SVG
charts with no chart library; Tailwind tokens generated from `theme.py` and guarded by a design
gate.

**Progress:** Task 0 (repo relocation) done. Task 1 (team colour resolver) `338d976`. Task 2
(token bridge + drift gate) `64b935e`. Task 3 (dataset export — 11 files, 87.6 KB) `1d7c463`.
Task 4 (Next.js skeleton, 103 kB First Load JS, all routes static) `752a8d7`. Task 5 (home page:
hero, `CourtZones` shot-efficiency court, leaders, team ratings) `b924457`. Task 6 (About page,
JSON-LD, generated OG card) done. Task 7 (Vercel deploy) done 2026-07-31.

Confirmed by the user 2026-07-31: LinkedIn `https://www.linkedin.com/in/sasha-risoluti/`; the
live dashboard is `https://hoopslab.streamlit.app/`. There is still **no custom domain** — note
that `hoopslab.streamlit.app` is Streamlit Community Cloud and cannot host the Next.js app, so
`site.url` currently holds the expected Vercel URL and must be corrected at deploy time.

Visual verification is set up: Playwright lives in the session scratchpad (`verify/shot.mjs`) and
screenshots the running app at 1440px and 360px while checking for horizontal overflow and console
errors. Two real defects in Task 5 were invisible to the test suite and only surfaced this way —
always screenshot before calling a page done.

Build the web app with `cd web && npm run build`. It needs `NODE_EXTRA_CA_CERTS` set to the CA
bundle (already a user env var) or `next/font/google` fails behind the corporate proxy — see
[[hoops-lab-corporate-tls-git-lfs]].

Still open: no custom domain (the site uses the free `*.vercel.app`).

**Colour finding, corrected by measurement:** the reference's 52% lightness floor does not apply
here. Against this project's much darker `BG_PAGE` `#070b14`, only **1 of 30** accents (SAC, 1.99)
fails WCAG 3:1 for graphical objects — not 18. `ensure_contrast` lifts only what fails, so exactly
one accent changed. The duplicate-hex collisions (ATL/POR, CHI/HOU/TOR, CLE/IND, DET/LAC, MIA/UTA)
are real but **latent**: no surface paints two team accents at once until Phase 3. `resolve_pair`
is built and tested but deliberately unwired.

## Reference project findings (2026-07-30)

`github.com/Alamyy/Worldcup26` is **not** the app — it is a CC BY 4.0 open-data publication
(21 CSVs, data dictionary, schema, `CITATION.cff`). The frontend repo is private; its
architecture was reverse-engineered from the deployed bundles: Vite + React 19 + Tailwind 3.4,
hand-rolled router, **no chart library, no UI library, no state library**.

Its CSS variables are token-for-token identical to what this project already adopted
(`#16c47f`, `#0052ff`, `#e0262c`, `#ffd100`, `#a855f7`, `#141c2e`), confirming the Phase A
extraction was accurate. Worth stealing: the team-colour contrast/collision resolver, the
promise-level fetch cache with retry-on-error, and the inlined-index-plus-lazy-detail data
pattern. Worth *not* copying: absent SEO, hand-rolled routing, no light mode.

## Deferred follow-ups from the restyle (all minor)

- Manual visual pass vs the reference site — watch page 02's radar for label clipping.
- `stat_tile` docstring: mention NaN omission for delta/pctl.
- `radar_chart.py` import line is exactly 100 chars — split when next touched.
- Radar AppTest rare 3 s timeout flake — bump when next touched.

## Standing user decisions

- Resolve review findings and plan conflicts with the recommended option; no mid-run questions.
- Push to `origin/main` is authorized; it redeploys both the Streamlit dashboard and the
  Vercel site.

## Environment warning

Clearing `__pycache__` and `.pytest_cache` is required after any file restore: stale bytecode
makes Streamlit AppTests fail with `OSError: could not get source code`, which looks alarming and
means nothing.
