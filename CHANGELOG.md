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
