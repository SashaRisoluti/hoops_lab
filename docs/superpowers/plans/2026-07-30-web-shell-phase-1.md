# Phase 1 — Foundation and First Impression

Spec: `docs/superpowers/specs/2026-07-30-web-shell-design.md`
Branch: `feature/web-shell-phase-1`
Status: not started

## Outcome

A statically generated Next.js site, deployed to Vercel on the custom domain, showing real NBA
data with zero cold start. Home page and About page only. Streamlit untouched and still green.

## Definition of done

- `python scripts/export_web_data.py` produces `web/public/data/*.json` inside the 2 MB budget.
- Tailwind tokens are generated from `theme.py`; a design gate fails if they drift.
- Deployed URL scores ≥95 on all four Lighthouse categories.
- Sharing the URL renders a correct Open Graph card.
- First-load JS under 150 KB gzipped.
- Existing Python suite still green: 228 tests, ruff clean, Streamlit boots 200.

## Task 0 — Move the repo off OneDrive (blocking)

Today's session lost `.git` plumbing and 20 source files to OneDrive conflict resolution. Adding
`node_modules` — tens of thousands of small files — to a synced folder makes recurrence near
certain and will also make every `npm install` crawl.

1. Push the current commit `2cc9e69` to origin so nothing lives only on this machine.
2. Clone fresh to `C:\dev\hoops-lab`.
3. Recreate `.venv`, reinstall, confirm the suite is green in the new location.
4. Keep the OneDrive copy read-only until Phase 1 lands, then delete it.

**Verify:** `git status` clean in the new path; 228 tests pass; no `*-MLNKSO-*` file appears after
an hour of normal work.

> Do not start Task 1 until this is done. Everything downstream assumes a stable filesystem.

## Task 1 — Team colour resolver (Python) — ✅ DONE

Delivered: `hoops_lab/visuals/team_colors.py` (42 tests), `TEAM_ACCENTS_READABLE` in `theme.py`,
wired into both accent call sites (`dashboard/app.py`, `dashboard/components/team_rail.py`).

**Two deviations from the original plan, both driven by measurement:**

1. **The fixed 52% lightness floor was rejected.** Measured against the real `BG_PAGE` `#070b14`,
   only 1 of 30 accents (SAC, 1.99) fails WCAG 3.0 for graphical objects — not 18. The floor
   would have pushed BOS `#007A33` to a neon `#0aff71` at contrast 14.58 for no accessibility
   gain. Replaced by `ensure_contrast(value, background, min_ratio=3.0)`, which lifts by the
   smallest step that clears the measured ratio and returns the colour untouched otherwise.
   Net palette change: 1 of 30 — SAC `#5A2D81` → `#7f3fb6` (1.99 → 3.08).
2. **A single +22° rotation does not guarantee separation.** `#CE1141` sits near the red end of
   the wheel where a small hue change barely moves the colour in RGB space; one step lands only
   ~52 units away, under the 90 threshold. `resolve_pair` now steps repeatedly until the pair is
   genuinely distinguishable.

`resolve_pair` is implemented and tested but has **no call site yet** — no surface paints two team
accents at once until Phase 3 adds head-to-head pages. Kept deliberately, flagged deliberately.

**Verified:** 256 unit + 14 integration tests green, ruff clean, dashboard boots HTTP 200. Tests
cover every exact-duplicate group (ATL/POR, CHI/HOU/TOR, CLE/IND, DET/LAC, MIA/UTA), exact
`hex→hsl→hex` round-tripping for all 30 accents, hue and saturation preservation under lift, and
a regression guard asserting that no already-readable accent is modified.

## Task 2 — Token bridge — ✅ DONE

Delivered: `scripts/export_web_data.py --tokens-only` writes `web/tokens.json`; the drift gate
`test_web_tokens_artifact_matches_theme` lives in `tests/unit/test_design_gates.py`; export
behaviour is covered separately by `tests/unit/test_web_export_tokens.py`.

Extension beyond the original plan: the payload also carries `teamAccents`
(`TEAM_ACCENTS_READABLE`), so the web app never re-derives team colours in TypeScript and Task 1's
contrast work is inherited for free. Output is deterministic — no timestamp — otherwise every
export would diff and the gate would be noise.

Also fixed here, from the deferred follow-up list: the `test_chart_components_colors` flake. It
was running against Streamlit's 3s default script timeout while the AppTest apps need up to ~16s
to import pandas and plotly on a loaded machine. Timeout raised to 30s; assertions untouched;
verified stable across three consecutive runs.

**Verified:** gate goes red when a token is edited without re-exporting (demonstrated); 264 unit
+ 14 integration tests green; ruff clean; dashboard boots HTTP 200.

## Task 3 — Data export

`scripts/export_web_data.py` full implementation. Calls existing `hoops_lab.analytics` functions
only — no new analytics.

Writes `index.json`, `leaders/{season}.json`, `archetypes/{season}.json` for the demo seasons.
Team and player detail files are deferred to Phase 3.

Include `generatedAt` and `generatedFrom` stamps in `index.json`.

**Verify:** new `tests/unit/test_web_export.py` runs the export against an in-memory `Database`
seeded with fixture frames; asserts every emitted file parses as JSON, matches its expected key
set, and that total bytes stay under 2 MB. Numbers for one known player are asserted equal to the
values the Streamlit page shows for the same season.

## Task 4 — Next.js skeleton

`web/` — Next.js App Router, TypeScript, Tailwind. `tailwind.config.ts` imports `tokens.json`.

- `AppShell`: topbar, desktop sidebar, mobile dropdown at ≤980 px.
- `StatTile`, `PageHeader` ported from the Streamlit versions — same names, same props shape.
- `app/layout.tsx` with base metadata; `app/sitemap.ts`; `app/robots.ts`.
- `prefers-reduced-motion` block that also resets opacity and transform.

**Verify:** `npm run build` succeeds with zero type errors; `npx serve` renders the shell; axe
reports no violations on the shell; keyboard tab order reaches every nav item.

## Task 5 — Home page

Hero leads with real league data plus the signature archetype visual, per the confirmed brief.

- Real current-season leaders and team ratings from `index.json` and `leaders/`.
- A static preview of the archetype court map — the full interactive version lands in Phase 2.
- Honest "Live dashboard" call-to-action noting the ~30 s wake time.
- Footer showing `generatedAt` so data age is never hidden.

**Verify:** no horizontal scroll at 360 px; numbers on the page match the export fixtures;
Lighthouse ≥95 on all four categories locally.

## Task 6 — About page

Engineering story: architecture diagram, data flow, stack, test counts, links to GitHub and the
Streamlit demo. JSON-LD `Person` and `Dataset`.

**Verify:** structured data passes Google's Rich Results test; every outbound link resolves 200.

## Task 7 — Deploy

Vercel project with root directory `web/`, custom domain, HTTPS.

**Verify:** deployed URL scores ≥95 across all four Lighthouse categories; the OG card renders
correctly in a real link preview; first-load JS under 150 KB gzipped; the domain serves over
HTTPS with a valid certificate.

## Task 8 — Close

Update `README.md` (the interface table still says "Phase 1" for the dashboard — stale),
`CHANGELOG.md`, and `docs/superpowers/RESUME.md`.

**Verify:** full Python suite green; ruff clean; Streamlit boots 200; `web/` builds clean.

## Open items to resolve before Task 6

- Actual domain (placeholder `hoopslab.dev` is in the metadata config).
- LinkedIn URL; whether to display an email address.
- Confirm product-branded naming with author credit, rather than personal branding.

## Sequencing note

Tasks 1–3 are Python-only and independently valuable — they improve Streamlit even if the web app
is never built. Tasks 4–7 are the web app. If appetite drops after Task 3, stopping there still
leaves the codebase better than it started.
