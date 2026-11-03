# Win Probability on `/live` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fit a drifting-lead win-probability model in Python, export it to the website, and show the selected game's win probability, ESPN's line, and the score margin on one chart under the `/live` scorebar.

**Architecture:**
- **Python (`hoops_lab/models/game_win_probability.py`):** leak-free pregame net ratings, game states, the logistic fit, and the metrics.
- **Export (`scripts/export_web_data.py`):** gates the model and writes `web/public/data/win-probability.json`.
- **Web:** pure TS in `web/lib/live/winprob.ts` computes the series; a presentational card draws the chart; `LiveGame` wires it in.

**Tech Stack:** Python 3.13, pandas, scikit-learn (already pinned), pytest; Next.js 15, TypeScript, `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-03-live-win-probability-design.md`

## Global Constraints

- No new dependency (Python or npm). `requirements.txt` is the deploy lock.
- `dashboard/` imports nothing from the new module (Streamlit Cloud reloads only `dashboard/` on push). The new module is imported only by `scripts/` and tests.
- Training margin is summed from scoring events (`features.possession._event_points` after `sort_chronological`), never from `scoreHome`/`scoreAway`.
- Pregame prior is leak-free: same-season games with `GAME_DATE < D` only. `k = 10`. The first season's last-season NR is 0.
- Model: `f = max(secondsRemaining, 1)/2880`; `z = a·margin/√f + b·√f·(1−neutral) + c·ΔNR·√f`; `P = 1/(1+e^−z)`; `LogisticRegression(fit_intercept=False, penalty=None)`.
- Gate thresholds are never relaxed: held-out log-loss < baseline; ECE (10 bins) ≤ 0.05; pregame log-loss < constant home rate. Held-out = the last two `DEMO_SEASONS`; train = the rest.
- No hex literals in `web/app|components|lib` (design gate). Colours come from tokens or team accents only.
- `web/lib/live/*` modules import each other only with `import type`. Tests import with `.ts` extensions and use `node:test`.
- Code, comments and UI copy in English. Python: type hints and docstrings; never mutate inputs; never inf.
- Parallel agents share one tree: **no git by agents**; each agent touches only its listed files and runs only its own tests. The controller commits.

## Review Focus

1. **Overtime and end of game:** `secondsRemaining = 0` must not divide by zero (f floor). OT elapsed time extends the chart axis. Pinned in Tasks 1 and 3.
2. **Leakage:** a game's own result must never enter its training prior. Pinned in Task 1 (date-strict test).
3. **Unknown matchups** (All-Star teams, preseason, a team missing from priors): no number is shown. Pinned in Tasks 3 and 6.
4. **ESPN payload gaps** (no `winprobability`, plays without a score): never throw. Pinned in Tasks 2 and 3.
5. **Gate failure:** the export still writes a file with `available: false`, so the web build never breaks. Pinned in Task 5.

## Waves

| Wave | Tasks (parallel) | Needs |
|---|---|---|
| 0 | Controller contract: types + placeholder JSON | — |
| 1 | T1 Python model · T2 ESPN parsing · T3 `winprob.ts` · T4 chart card | Wave 0 |
| 2 | T5 gate + export (needs T1) · T6 LiveGame wiring (needs T2, T3, T4) | — |
| 3 | Final review, fixes, browser checks, docs, release | all |

---

### Task 0 (controller): web contract

- `web/lib/live/types.ts`:
  - `Play.id: string`, `Play.homeScore: number`, `Play.awayScore: number` (running score after the play);
  - `GameSummary.neutralSite: boolean`, `seasonType: number`, `espnWinProbability: { playId: string; home: number }[]`;
  - `ScoreboardGame.neutralSite: boolean`, `seasonType: number`;
  - new types `WpPoint = { t: number; home: number; margin: number }`, `EspnWpPoint = { t: number; home: number }`, and `WinProbModel` (the JSON shape below).
- `web/public/data/win-probability.json` placeholder: `{ "available": false }`, so imports compile until Task 5 writes the real file.
- `WinProbModel` (the export JSON):
  ```
  { available: boolean;
    coefficients?: { a: number; b: number; c: number };
    homeCourtPts?: number; pointsPerNetRating?: number; scale?: number;
    k?: number; season?: string; asOf?: string;
    teams?: Record<string, number>;            // NBA tricode → pregame net rating
    metrics?: { trainGames: number; holdoutGames: number;
                holdoutLogLoss: number; baselineLogLoss: number; ece: number;
                pregameLogLoss: number; constantLogLoss: number } }
  ```

### Task 1: Python model library

**Files:** Create `hoops_lab/models/game_win_probability.py`, `tests/unit/test_game_win_probability.py`.

**Interfaces — Produces:**
- `team_game_ratings(box: pd.DataFrame) -> pd.DataFrame`. Input: `box_scores_team` rows. Output: one row per team-game with `GAME_ID, TEAM_ID, TEAM_ABBREVIATION, GAME_DATE, season, pts, opp_pts, poss`. `poss` = the mean of both teams' `FGA + 0.44·FTA − OREB + TOV`.
- `pregame_priors(box: pd.DataFrame, k: float = 10.0) -> pd.DataFrame`: `GAME_ID, TEAM_ID, n_prior, nr_to_date, nr_last_season, prior`, where `prior = (n·nr_to_date + k·nr_last_season)/(n+k)`.
- `current_priors(box: pd.DataFrame, season: str, k: float = 10.0) -> tuple[dict[str, float], str]`: tricode → prior after every game of `season`, plus the as-of date (`YYYY-MM-DD`).
- `build_states(pbp: pd.DataFrame, games: pd.DataFrame, priors: pd.DataFrame) -> pd.DataFrame`: `game_id, season, margin, seconds_remaining, neutral, prior_diff, home_won`. One opening state (margin 0, seconds 2880) per game, plus one state per scoring event.
- `features(states: pd.DataFrame) -> np.ndarray`: columns `[margin/√f, √f·(1−neutral), prior_diff·√f]`.
- `fit(states) -> LogisticRegression`; `predict(model, states) -> np.ndarray`; `coefficients(model) -> dict[str, float]` (`a, b, c, homeCourtPts=b/a, pointsPerNetRating=c/a, scale=1/a`).
- `expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float`.

- [ ] **Step 1: Write the failing tests** (synthetic frames, exact values):
  - Possessions: FGA 90, FTA 20, OREB 10, TOV 15 → 103.8 for that team. The game's `poss` = mean with the opponent's estimate.
  - **Leak-free priors** (both teams' estimates 100 possessions in every game). Three 2021-22 games:
    - G1 2021-10-20: A 110–100 B;
    - G2 2021-10-22: A 95–105 C;
    - G3 2021-10-24: A 102–98 B.

    Expected priors:
    - A before G3: n=2, `nr_to_date` 0.0, prior 0.0;
    - B before G3: n=1, `nr_to_date` −10.0, prior `−10/11 ≈ −0.909091`;
    - A before G1: n=0, prior 0.0;
    - a 2022-23 first game of A: `nr_last_season` = 100·(10 − 10 + 4)/300 ≈ 1.333333 = prior.
    - A same-date second game must not see the first: the strict `<` check.
  - `current_priors` for 2021-22 → A = (3·1.333333 + 10·0)/13 ≈ 0.307692; as-of "2021-10-24".
  - States from events (PBPv3 clocks like `PT11M00.00S`):
    - home made 2 ("Made Shot", `shotValue` 2) at Q1 11:00;
    - away made FT ("Free Throw", no "MISS") at Q1 10:30;
    - away missed FT ("MISS ...");
    - `scoreHome` set to a wrong "99" everywhere.

    Expected states: (margin 0, 2880), (2, 2820), (1, 2790). There is no state for the miss, and the margin ignores the 99.
  - Overtime: an event at period 5 `PT04M58.00S` gives `seconds_remaining` 298.
  - Features for margin 6, seconds 720, neutral False, prior_diff 4: `[12.0, 0.5, 2.0]`. With neutral True the middle value is 0.0. With seconds 0, f = 1/2880 (no inf).
  - ECE: `y=[1,0,1,1]`, `p=[0.9,0.1,0.8,0.3]` → 0.275.
  - `coefficients` on a model with `coef_ = [[0.1, 0.3, 0.05]]` → `homeCourtPts` 3.0, `pointsPerNetRating` 0.5, `scale` 10.0.
  - Inputs are not mutated.
- [ ] **Step 2:** `.venv\Scripts\python.exe -m pytest tests/unit/test_game_win_probability.py -q` FAILS (module missing).
- [ ] **Step 3: Implement** (vectorised pandas; reuse `_event_points`, `sort_chronological`, `_clock_seconds`; the event team comes from `teamId` against `games.home_team_id`).
- [ ] **Step 4:** the same command PASSES; then `ruff check` and `ruff format --check` on the two files are clean.

### Task 2: ESPN parsing additions

**Files:** Modify `web/lib/live/espn.ts`, `web/tests/live/espn.test.ts`.

**Interfaces — Consumes:** the Task 0 types. **Produces:** `parseSummary` fills `Play.id`, `Play.homeScore`/`awayScore` (ESPN `homeScore`/`awayScore`, default 0), `neutralSite`, `seasonType`, `espnWinProbability`; `parseScoreboard` fills `neutralSite` and `seasonType`.

- [ ] **Step 1: Failing tests** (clone the parsed fixtures' raw JSON in-test and add fields; do not edit fixture files):
  - Play ids: the play with seq 72 has `id` "40190990372".
  - Summary raw with `winprobability: [{homeWinPercentage: 0.376, playId: "4019099034"}, …]` → `espnWinProbability[0]` = `{playId: "4019099034", home: 0.376}`; a missing array → `[]`.
  - Summary raw with `header.season.type = 3` → `seasonType` 3; missing → 2.
  - `header.competitions[0].neutralSite = true` → `neutralSite` true; missing → false.
  - Scoreboard: an event with `season: {type: 1}` and `competitions[0].neutralSite: true` → 1 / true; the existing fixtures → 2 / false.
  - All previous assertions still pass.
- [ ] **Step 2–4:** `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test tests/live/espn.test.ts`: RED, then GREEN; `npx tsc --noEmit` clean for `espn.ts`.

### Task 3: `winprob.ts` (pure)

**Files:** Create `web/lib/live/winprob.ts`, `web/tests/live/winprob.test.ts`.

**Interfaces — Produces:**
- `homeWinProbability(model: WinProbModel, x: { margin: number; secondsRemaining: number; priorDiff: number; neutral: boolean }): number | null` (null when `!model.available`).
- `priorDiff(model: WinProbModel, homeTricode: string, awayTricode: string): number | null` (null if either tricode is missing).
- `secondsRemaining(period: number, clock: string): number` and `elapsedSeconds(period: number, clock: string): number` (ESPN "M:SS" and "S.s"; quarters are 720 s, OT 300 s).
- `wpSeries(summary: GameSummary, model: WinProbModel, prior: number): WpPoint[]`: the pregame point at t=0, then one point per play whose score changed. For a `post` game the last point is 1/0 by the final score.
- `espnSeries(summary: GameSummary): EspnWpPoint[]`: aligned to plays by `id`; unknown ids are dropped.
- `wpAvailable(model, seasonType, prior)`: false for preseason (1), a null prior, or an unavailable model.

- [ ] **Step 1: Failing tests** with `model = { available: true, coefficients: { a: 0.1, b: 0.3, c: 0.05 }, teams: { ORL: 2, BOS: -2 } }`:
  - margin 6, secondsRemaining 720, priorDiff 4, neutral false → 0.809998 (±1e-6); neutral true → 0.785835; pregame (0, 2880, 4, false) → 0.622459; margin 1 at 0 s → 0.995394.
  - `priorDiff(model, "ORL", "BOS")` = 4; an unknown tricode → null; `available: false` → `homeWinProbability` null.
  - Clocks:
    - `elapsedSeconds(1,"12:00")` 0, `(2,"5:30")` 1110, `(4,"0.0")` 2880, `(4,"9.1")` 2870.9, `(5,"4:58")` 2882;
    - `secondsRemaining(3,"4:58")` 1018, `(5,"4:58")` 298.
  - `wpSeries(final fixture)`: first point `{t: 0, margin: 0}`; last point margin −11 and home 0 (ORL lost 97–108); points sorted by t; margins match the plays' `homeScore − awayScore`.
  - `wpSeries(live fixture)`: last point margin −10 (59–69), home in (0,1).
  - `espnSeries` with two known ids and one unknown → 2 points carrying the plays' t.
  - `wpAvailable`: seasonType 1 → false; prior null → false.
- [ ] **Step 2–4:** `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test tests/live/winprob.test.ts`: RED, then GREEN; tsc clean for the file.

### Task 4: `WinProbabilityCard` (presentational)

**Files:** Create `web/components/live/WinProbabilityCard.tsx`.

**Interfaces — Produces:** `WinProbabilityCard({ homeTricode, awayTricode, homeAccent, awayAccent, state, current, pregame, series, espn, periods, asOf, metrics }: { …strings; state: GameState; current: number | null; pregame: number; series: WpPoint[]; espn: EspnWpPoint[]; periods: number; asOf: string; metrics: { trainGames: number; holdoutLogLoss: number; baselineLogLoss: number } })`

- Layout A (mockup `wp-layout-v2`):
  - headline: away % on the left and home % on the right, each with tricode + accent swatch (`ring-1 ring-ink-soft`); a split bar;
  - an SVG chart:
    - x = elapsed seconds over `[0, 2880 + max(0, periods − 4)·300]`, with quarter/OT gridlines;
    - left y = home WP, home tricode top, away bottom, 50% dashed midline;
    - right y = margin, symmetric ±M with `M = max(10, ceil(max|margin|/5)·5)` and 0 on the midline;
    - margin is a muted stepped area plus line behind; ESPN a dashed line; our model a solid line; a dot on the latest point when `state === "in"`;
  - a legend (Hoops Lab model · ESPN · score margin, right axis);
  - a footnote: `Pregame: <TRI> NN% (season net rating + home court, as of <asOf>) · fitted on <trainGames> games · held-out log-loss <x> vs <baseline>`.
- `state === "pre"`: headline + split bar from `pregame`, and the footnote; no chart.
- Use the `dataviz` skill for the chart (invoke the Skill tool with `dataviz` if available). Token classes only, no hex literals; accents arrive as props.
- [ ] **Step 1:** Implement. **Step 2:** `npx tsc --noEmit` clean for the file; the hex grep on the file prints nothing.

### Task 5: Gate + export

**Files:** Modify `hoops_lab/models/game_win_probability.py` (add `evaluate_holdout(db) -> dict` and `gate_passes(metrics) -> bool`), `scripts/export_web_data.py` (`build_win_probability(db) -> dict`; `export_dataset` writes `win-probability.json`). Create `tests/integration/test_game_wp_gate.py`. Modify `tests/unit/test_web_export_dataset.py`. Regenerate `web/public/data/win-probability.json`.

**Interfaces — Consumes:** Task 1. **Produces:** the real JSON in the Task 0 shape.

- `evaluate_holdout`:
  - train = `DEMO_SEASONS[:-2]`, held-out = `DEMO_SEASONS[-2:]` (PBP states);
  - baseline = the existing `train_win_probability` / `predict_wp_frame` on the same states (`minutes_remaining = seconds/60`);
  - pregame check over all held-out-season `games` rows;
  - returns the `metrics` fields.
- `gate_passes`: `holdoutLogLoss < baselineLogLoss and ece <= 0.05 and pregameLogLoss < constantLogLoss`.
- `build_win_probability`: `available: gate_passes(metrics)`. When true, it refits on all seasons and adds the coefficients, the `current_priors(newest season)`, `asOf` and `k`. When false, it writes `{available: false, metrics}`.
- If the gate fails: try the in-family variants the spec allows (f exponent, k ∈ {5, 10, 20}) and **report** which passes. Never relax thresholds. If none passes, ship `available: false`.
- [ ] **Step 1: Failing tests:**
  - unit: `export_dataset` on the in-memory test DB writes `win-probability.json` with the `available` key;
  - unit: `gate_passes` truth table;
  - integration (skips without the DB): `gate_passes(evaluate_holdout(Database()))` is True and prints the metrics.
- [ ] **Step 2–4:** RED → GREEN. Run `.venv\Scripts\python.exe scripts/export_web_data.py`, then the full unit suite, the new integration test and ruff.

### Task 6: LiveGame wiring

**Files:** Modify `web/components/live/LiveGame.tsx`.

**Interfaces — Consumes:** Tasks 2–4; `@/public/data/win-probability.json` as `WinProbModel`.

- Render `WinProbabilityCard` **directly under the scorebar, above the court**, for the selected game:
  - prior = `priorDiff(model, home, away)`;
  - pregame = `homeWinProbability(model, {margin 0, secondsRemaining 2880, priorDiff, neutral})`;
  - for `in`/`post`: `wpSeries`, `espnSeries`, `current` = last point;
  - `periods` = max(4, `summary.period`).
- When `wpAvailable` is false: `<Note>Win probability not available for this matchup.</Note>`.
- Scheduled game: use the scoreboard game's `neutralSite` and `seasonType`.
- [ ] **Step 1:** Implement. **Step 2:** `npm test`, `npx tsc --noEmit`, the hex grep and `npm run build` all pass.

### Task 7 (controller): verification, docs, release

- Full Python suite, web gates.
- Browser checks (headless Edge, normal UA):
  - real ESPN: yesterday's finals, a scheduled game;
  - the simulated in-progress game through CDP interception;
  - 375 px.
- Docs: CHANGELOG, README `/live` paragraph, RESUME, and the CLAUDE.md "Models" bullet.
- Push `main` (no Streamlit reboot needed: `dashboard/` is untouched), then check production `/live` and the hosted dashboard.
