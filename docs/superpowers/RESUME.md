# Session Resume Point

Last updated: 2026-07-30.

## Current state

- **Worldcup26 UI restyle (Phase A + B): COMPLETE and merged.** Phase A at `ef4c8fc`, Phase B
  `d278796..bba45af`, resume-point commit `2366992`.
- **2026-07-30: OneDrive corruption recovered.** A PC shutdown mid-session left OneDrive
  renaming `.git/HEAD`, `refs/heads/main` and `index` into `*-MLNKSO-NW1DRNQ` copies, and
  reverting 20 source files to older content while the newest content sat in conflict copies.
  Fully recovered; all 76 conflict copies removed. Verified: 214 unit + 14 integration tests
  green, ruff clean, dashboard boots HTTP 200.
- Local `main` is at `2cc9e69` (recovered CLAUDE.md documentation), **one commit ahead of
  `origin/main`** — not yet pushed.

## Next work: public web shell

Brainstormed and specced on 2026-07-30. Not started.

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

**Blocking first task:** move the repo out of OneDrive to `C:\dev\hoops-lab` before any `npm`
work. `node_modules` in a synced folder makes today's corruption near-certain to recur.

**Highest-value single item, verified against real data:** `TEAM_ACCENTS` has five groups sharing
a byte-identical hex covering 11 of 30 teams (ATL/POR, CHI/HOU/TOR, CLE/IND, DET/LAC, MIA/UTA),
and 18 of 30 accents fall below 52% lightness on the dark surface. Head-to-head charts for those
pairs are currently unreadable. The fix is a Python colour resolver that benefits Streamlit too —
Phase 1, Task 1.

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
- `README.md` interface table still says "Phase 1" for the dashboard — stale, fix in Phase 1 Task 8.

## Standing user decisions

- Resolve review findings and plan conflicts with the recommended option; no mid-run questions.
- Push to `origin/main` (triggers the HF Spaces deploy) was authorized at the end of Phase B.

## Environment warning

Clearing `__pycache__` and `.pytest_cache` is required after any file restore: stale bytecode
makes Streamlit AppTests fail with `OSError: could not get source code`, which looks alarming and
means nothing.
