# Public Web Shell — Design Spec

Date: 2026-07-30
Status: proposed (brainstorming session)
Reference: https://worldcup26-analyticslab.vercel.app/ (Vite + React 19 + Tailwind 3.4 SPA, private source)
Reference dataset: https://github.com/Alamyy/Worldcup26 (CC BY 4.0 open data — *not* the app source)

## Goal

Give hoops-lab a public front door: a statically generated web app on Vercel, served from the
user's own domain, that renders **real NBA data** exported from DuckDB at build time. It carries
the first impression for recruiters with zero cold start, and links onward to the existing
Streamlit dashboard for deep interactive work.

The Python package `hoops_lab/` remains the single source of truth for all analytics. No stat
logic is reimplemented in TypeScript.

## Understanding lock (confirmed 2026-07-30)

- **Purpose**: portfolio piece to get hired. Recruiters first, reviewing engineers second.
- **Depth**: hybrid — React shell alongside Streamlit, not a full migration.
- **Appetite**: large; multi-week phased build is acceptable.
- **Data**: real, exported as static JSON. No live backend, no `api/` build-out.
- **Cold start**: the static site carries the first impression; the Streamlit link is framed
  honestly as "may take ~30s to wake".
- **Hero**: live league data *and* the signature shot-archetype visual.
- **Hosting**: Vercel, custom domain (see open items).

## Non-goals

No Streamlit retirement. No FastAPI backend. No auth, no accounts, no CMS, no i18n, no
server-side data fetching, no real-time updates.

## Decisions

| Decision | Choice | Alternatives rejected |
|---|---|---|
| Framework | Next.js App Router, fully static | Astro (fights later absorption of analytics pages); Vite SPA (no SEO — the reference's fatal flaw) |
| Styling | Tailwind, tokens generated from `theme.py` | Hand-written CSS (drifts from Streamlit) |
| Charts | Bespoke SVG components, no chart library | Recharts/D3 (two visual systems drift; design gates exist to prevent exactly that) |
| Data | Build-time JSON export, committed | Live API (hosting cost, cold start); DB in browser (payload) |
| Repo layout | `web/` inside this repo | Separate repo (splits the portfolio narrative) |
| Token source of truth | Python `TOKENS` in `theme.py` | Duplicated Tailwind config (guaranteed drift) |

## 1. Architecture

```
hoops-lab/
├─ hoops_lab/              # unchanged — analytics engine, source of truth
├─ dashboard/              # unchanged — Streamlit deep tool
├─ scripts/
│   └─ export_web_data.py  # NEW  DuckDB -> web/public/data/*.json + tokens.json
├─ web/                    # NEW  Next.js app (Vercel root directory)
│   ├─ app/                # routes + metadata + sitemap + robots
│   ├─ components/         # mirrors dashboard/components names 1:1
│   ├─ lib/                # data loaders, formatting, color utils
│   ├─ public/data/        # generated JSON (committed)
│   └─ tailwind.config.ts  # reads generated tokens.json
└─ docs/
```

Data flow:

```
nba_api -> parquet -> DuckDB -> hoops_lab analytics
                                   |                    \
                        export_web_data.py          Streamlit (live, interactive)
                                   |
                        web/public/data/*.json
                                   |
                        Next.js SSG -> Vercel -> custom domain
```

### Token bridge (single source of truth)

`theme.py` already exposes `TOKENS: dict[str, str]` and `tokens_json()` at
[theme.py:139](../../../dashboard/components/theme.py). The export script writes
`web/tokens.json`; `tailwind.config.ts` imports it and expands it into the theme.

A new design gate asserts the generated `tokens.json` matches `TOKENS` exactly, extending the
existing gate family in `tests/unit/test_design_gates.py`. Streamlit and web cannot visually
diverge without a red test.

## 2. Data export contract

`scripts/export_web_data.py` — a thin caller of existing `hoops_lab.analytics` functions. It
adds no new analytics.

| File | Contents | Budget |
|---|---|---|
| `index.json` | seasons, 30 teams, player index (id, name, tricode, slug), summary counts | < 150 KB |
| `leaders/{season}.json` | top-N per stat category | < 80 KB |
| `teams/{tricode}.json` | ratings, Four Factors, recent form, percentile vector | < 30 KB each |
| `players/{id}.json` | profile, percentile radar vector, shot-zone profile | < 20 KB each |
| `archetypes/{season}.json` | KMeans centroids, labels, feature drivers, example players, SOM grid | < 200 KB |

Total budget **< 2 MB**. Written only for the demo seasons in `DEMO_SEASONS`. Player detail files
are generated only for players above the existing minimum-sample thresholds, which caps file count.

Verification: a unit test runs the export against an in-memory `Database`, asserts every file
parses as JSON, conforms to its schema, and that the total stays inside budget.

### Freshness

Manual: re-run the export, commit, push. Vercel rebuilds. No scheduler in scope. `index.json`
carries a `generatedAt` stamp rendered in the site footer, so the data is never silently stale.

## 3. Routes

| Route | Purpose | Phase |
|---|---|---|
| `/` | Hero: real league data + signature archetype visual | 1 |
| `/about` | Engineering story, architecture diagram, stack, links | 1 |
| `/archetypes` | Shot-archetype explorer — the signature interactive piece | 2 |
| `/teams` and `/teams/[tricode]` | Team identity, Four Factors, form | 3 |
| `/players` and `/players/[id]` | Player card, percentile radar, shot profile | 3 |

All statically generated via `generateStaticParams`. Streamlit is linked from the nav as
"Live dashboard", with an honest wake-time note.

## 4. Components

Mirror the Streamlit component names exactly, so the two surfaces stay conceptually aligned:

`AppShell` (new — sidebar + topbar + mobile nav), `StatTile`, `PageHeader`, `SearchSelect`,
`InfoTooltip`, `TeamFlag`, `StatTable`, `PercentileBar`.

Chart primitives, all bespoke SVG: `BarCompare` (opposing horizontal bars), `LineArea`
(polyline + gradient polygon), `RadarChart`, `CourtMap` (NBA half court in ShotChartDetail
coordinates, drawn in SVG so shots stay interactive), `SomGrid`.

## 5. Team colour resolution (ported from the reference)

The reference ships the single most transferable piece of code in that app: a contrast-lift that
raises any team colour to ≥52% lightness for dark backgrounds, plus a collision resolver that
detects when two opposing colours are too close (Euclidean RGB distance < 90, or hue delta < 35°
with distance < 160) and rotates the second hue by 22°.

`TEAM_ACCENTS` has this problem measurably worse than the reference did. Verified against the
current values:

**Five groups share a byte-identical hex, covering 11 of 30 teams:**

| Hex | Teams |
|---|---|
| `#E03A3E` | ATL, POR |
| `#CE1141` | CHI, HOU, TOR |
| `#FDBB30` | CLE, IND |
| `#C8102E` | DET, LAC |
| `#F9A01B` | MIA, UTA |

This collision is **latent, not live**: as of Phase 1 no surface paints two team accents at once
— both call sites (`app.py`, `team_rail.py`) render only the selected team. It becomes a real
defect the moment Phase 3 ships head-to-head team pages, which is why `resolve_pair` exists now
and is tested now, but is not yet wired to anything.

### Correction: the lightness floor was wrong

The first draft of this spec claimed 18 of 30 accents were unreadable because they fall below the
reference's 52% lightness floor. **Measurement against this project's own background disproved
that.** `BG_PAGE` is `#070b14`, far darker than the reference's `#0a0f1c`, so most official
accents already have ample contrast. Measured WCAG ratios against `BG_PAGE`:

| Threshold | Accents failing |
|---|---|
| 3.0 (WCAG AA, graphical objects and large text) | **1 of 30** — SAC at 1.99 |
| 4.5 (WCAG AA, normal body text) | 15 of 30 |

The accent is painted as a chip ring, a glow and a header stripe — graphical objects, so 3.0 is
the governing threshold. Applying a 52% lightness floor would have "fixed" 18 colours that were
never broken, pushing Boston's `#007A33` to `#0aff71` (contrast 14.58, a neon green) and
destroying franchise identity for no accessibility gain.

**Implemented instead:** `ensure_contrast(value, background, min_ratio=3.0)` lightens by the
smallest step that clears the measured ratio, and returns the colour untouched when it already
passes. Net effect on the palette: **1 of 30 changed**, SAC `#5A2D81` → `#7f3fb6` (1.99 → 3.08).

The lesson generalises to the web app: verify contrast against the actual surface rather than
importing another project's heuristic.

Implemented in **Python** (`hoops_lab/visuals/team_colors.py`) so Streamlit and the web app both
benefit; `dashboard/components/theme.py` exposes `TEAM_ACCENTS_READABLE` and both call sites use
it.

## 6. SEO and accessibility

The reference has effectively none — only a `<title>`. Deliberately not copied.

- Per-route `metadata` exports: title, description, canonical, Open Graph, Twitter card.
- Dynamic OG images via `next/og` — team and player pages get cards showing real numbers.
- `app/sitemap.ts` and `app/robots.ts`.
- JSON-LD: `Dataset` schema on `/about`, `Person` for the author.
- Semantic HTML, one `<h1>` per page, keyboard-navigable `SearchSelect` with proper
  `role="combobox"` and `aria-activedescendant` (the reference gets this wrong).
- `prefers-reduced-motion` block that also resets opacity/transform, so reduced-motion users are
  not left with invisible content — the one accessibility detail the reference gets right.
- Contrast verified against WCAG AA for all token pairs, as a test.

## 7. Phases and success criteria

**Phase 1 — Foundation and first impression**
Export script, token bridge, Next.js skeleton, `AppShell`, `/` and `/about`, Vercel deploy.
Verify: export test green; token-parity gate green; Lighthouse ≥95 across all four categories on
the deployed URL; OG card renders correctly in a link preview; total JS < 150 KB gzipped.

**Phase 2 — Signature visual**
`/archetypes` with `CourtMap` and `SomGrid`.
Verify: renders on mobile at 360 px without horizontal scroll; interaction keyboard-accessible;
archetype numbers match the Streamlit page for the same season.

**Phase 3 — Entity pages**
`/teams`, `/players`, dynamic OG images, `SearchSelect` navigation.
Verify: every generated page has unique metadata; no 404 from any index link; team-colour
resolver applied on every head-to-head surface.

**Phase 4 — Open dataset (optional)**
Publish the derived NBA tables as a documented CC BY 4.0 dataset repo with a data dictionary,
schema, and `CITATION.cff` — mirroring what `Alamyy/Worldcup26` actually is. Cheap given the
pipeline already exists, and it differentiates from every other dashboard project.

## 8. Risks

| Risk | Mitigation |
|---|---|
| OneDrive corrupts the repo again mid-build | Move the repo out of OneDrive before Phase 1 starts |
| `node_modules` inside a synced folder is slow and corruption-prone | Same mitigation; blocking for Phase 1 |
| Export payload grows past budget | Size assertion in the export test fails the build |
| Streamlit and web visuals drift | Token-parity design gate |
| Scope creep into a full migration | Phases are independently shippable; stop after any of them |

## 9. Open items (defaults applied, override at will)

| Item | Default chosen | Needs your input |
|---|---|---|
| Domain | placeholder `hoopslab.dev` in metadata config | actual domain |
| Author links | GitHub + LinkedIn + email in footer and `/about` | LinkedIn URL, whether to show email |
| Branding | product-branded ("Hoops Lab"), author credited in header and `/about` | confirm |
| Language | English throughout | confirm |
| Page structure | adapted from the reference, not mirrored | confirm |

## Decision log

| # | Decision | Alternatives | Rationale |
|---|---|---|---|
| 1 | Hybrid shell, not full migration | Full React rewrite; Streamlit-only polish | Keeps all existing work; full migration stays an option rather than a bet |
| 2 | Next.js App Router | Astro; Vite SPA | Per-route SEO/OG is mandatory for a link-shared portfolio; absorption path stays cheap |
| 3 | Static JSON export | Live FastAPI; DuckDB-WASM | Zero cost, zero cold start, no secrets in the client |
| 4 | No chart library | Recharts; D3 | Reference proves SVG primitives are small; avoids two drifting visual systems |
| 5 | Tokens generated from `theme.py` | Hand-maintained Tailwind config | Drift is otherwise guaranteed; fits the existing design-gate culture |
| 6 | Colour resolver in Python, not TS | Port to TypeScript | Streamlit benefits too; engine stays the source of truth |
| 7 | `web/` in the same repo | Separate repo | One repo tells one story to a reviewing engineer |
| 8 | Repo moves out of OneDrive first | Keep in place | Today's corruption cost a full recovery session; `node_modules` makes recurrence near-certain |
