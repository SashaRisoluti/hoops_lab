# Live game page on the public web site — design

Date: 2026-11-02. Status: approved layout (visual mockup `live-layout-v2`), written for planning.

## Intent

The Streamlit dashboard cannot show live games when hosted: Streamlit Community Cloud sleeps
after about 12 idle hours, and both NBA sources (`cdn.nba.com`, `stats.nba.com`) are blocked
from its IPs. The public Next.js site (`web/`, Vercel, https://hoops-lab.vercel.app) never
sleeps. If the **visitor's browser** fetches the live data itself, the request leaves from the
visitor's IP and the cloud block no longer matters.

So: a new page, `/live`, rendered statically and filled entirely client-side from the ESPN
public API. A visitor opening it during an NBA game sees, within five seconds, the score, the
clock, which team has the ball, and each team's players with their stats.

## Goals

- `/live` on the existing site, reachable from the top navigation.
- For the selected game, top to bottom:
  1. **Scorebar**: both teams (tricode + score), period and clock, a LIVE marker with
     "updated N s ago" and the data source, team fouls in the current period and timeouts
     used, per team.
  2. **Court**: a full court with a central pill "`<TRI>` ATTACKING ►/◄" pointing at the basket
     of the team in possession, plus the last 10 shots of the game drawn on it (filled = made,
     hollow = missed, coloured by team accent). Below the court, the text of the last play.
  3. **Team comparison**: mirrored horizontal bars, away team left / home team right, for
     FG%, 3P%, REB, AST, STL, TO, PF.
  4. **Box score**: one tab per team. Columns `MIN PTS REB AST STL BLK TO PF FG 3PT FT +/-`.
     Players on court first, marked ●; bench below, visually dimmed; a bold team-totals row.
     A player's PF cell turns red at 5 or more.
- Auto-refresh every 30 s while the selected game is in progress.
- The Streamlit live page stays exactly as it is.

## Non-goals (this version)

- Win probability, alerts, live-vs-season comparison. They need the Python models and
  baselines; they can come later through a JSON export.
- Any NBA source. Verified on 2026-11-02: from a browser on `hoops-lab.vercel.app`,
  `cdn.nba.com` and `cdn-uat.nba.com` both fail (`TypeError: Failed to fetch`);
  `cdn-uat.nba.com` does not even resolve in public DNS. ESPN only.
- A server, an API route, a proxy or a cron. The page must keep working with Vercel serving
  static files only.

## Anti-goals

- A page that looks live but shows stale data without saying so. If a refresh fails, the page
  keeps the last data and says it is stale ("connection lost — retrying, last update hh:mm:ss").
- Hard-coded colours. The design gate `test_no_hex_literals_in_the_web_app` scans every
  `*.ts*` file under `web/app`, `web/components`, `web/lib`; colours come from
  `tokens.json` / Tailwind tokens only. Never weaken the gate.
- Breaking the existing site or the Python suite.

## Data source: ESPN public API (verified 2026-11-02)

Both endpoints answer `200` with `Access-Control-Allow-Origin: *`, also from a real browser on
the production origin.

- Scoreboard: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard`
  (optional `?dates=YYYYMMDD`). `events[]` with `id`, `name`, `date`, `status.type`
  (`state`: `pre` | `in` | `post`), `competitions[0].competitors[]` (`homeAway`, `team`,
  `score`).
- Game: `.../summary?event=<id>`.
  - `header.competitions[0]`: `status` (period, clock, state), `competitors[]` with
    `homeAway`, `team`, `score`, `linescores`, and **`possession` (boolean)**. On a finished
    game both are `false`; whether it is reliably `true` for the team with the ball during a
    live game is **not yet verified** (no game was live while designing).
  - `boxscore.players[]` (one per team): `statistics[0].labels` =
    `MIN PTS FG 3PT FT REB AST TO STL BLK OREB DREB PF +/-` and `athletes[]` with
    `athlete {id, displayName, shortName, jersey, position}`, `starter`, `active`,
    `didNotPlay`, `reason`, `ejected`, `stats[]` (strings, same order as `labels`).
    Map stats **by label**, never by position.
  - `boxscore.teams[]`: `statistics[]` with `name`/`displayValue`, including
    `fieldGoalPct`, `threePointFieldGoalPct`, `totalRebounds`, `assists`, `steals`,
    `turnovers`, `fouls`.
  - `plays[]`: `id`, `sequenceNumber`, `type.text`, `text`, `period.number`,
    `clock.displayValue`, `team.id`, `homeScore`, `awayScore`, `scoringPlay`, `scoreValue`,
    `shootingPlay`, `coordinate {x, y}`, and on some plays `participants[]`.
    - **Substitution**: `type.text == "Substitution"`, `text` "A enters the game for B",
      `participants = [entering, leaving]` (athlete ids). Lineup changes between periods also
      appear as substitutions at the period start.
    - **Shots**: `shootingPlay && !/Free Throw/`; `team.id` is the shooter's team.
      `coordinate` is in feet in the shooting team's half court: hoop at about (25, 0),
      `x ∈ [0, 50]` across the court, `y` = feet from the hoop towards midcourt (observed
      0–68, the high values being heaves). Checked against the text: "2-foot layup" at (27, 2),
      corner "22-foot three" at (2, 1). Non-shot plays carry a sentinel
      (`-214748340, -214748365`).
- ESPN team abbreviations differ from NBA tricodes for a few teams (e.g. `GS`, `NY`, `SA`,
  `NO`, `UTAH`, `WSH`). Team accents live in `tokens.json` → `teamAccents`, keyed by NBA
  tricode, so a small ESPN→NBA tricode map is needed; an unmapped team falls back to the
  `primary` token.
- The API is public but undocumented: it can change without notice. Parsing must be
  defensive (missing fields → the section shows "not available", the page does not crash).
- Privacy (owner's decision: load automatically, no consent button): the page credits
  "Data: ESPN" and carries one short line saying live data is loaded by the visitor's browser
  directly from ESPN's public API.

## Derived values (decided)

- **On court**: start from `starter == true` per team, then apply substitutions in play
  order (`participants[0]` in, `participants[1]` out). Do not rely on `active`: its meaning
  during a live game is unverified.
- **Possession**: use `competitors[].possession` when one team is `true`. Otherwise infer
  from the latest relevant play: rebound → the rebounding team; turnover → the other team;
  made field goal → the other team; last free throw of a trip made → the other team; jump
  ball → the play's team; end of period → nobody (hide the pill). A play that settles nothing
  (missed shot, foul, timeout, substitution) keeps the previous answer.
- **Team fouls (current period)**: count the current period's foul plays per team, excluding
  offensive and technical fouls (NBA penalty rules). Count only; no bonus logic.
- **Timeouts**: ESPN gives no "timeouts remaining", so the scorebar shows **timeouts used**,
  counted from timeout plays per team.
- **Court orientation**: home team attacks the right basket, away the left, for the whole game
  (the real half-time switch is ignored; ESPN coordinates are already per team half, so each
  team's shots land in front of its own basket consistently).

## Game selection and empty states (my call — the owner did not specify)

- On load, fetch the scoreboard for ESPN's default day (no `dates` parameter). If that day has
  no game that is in progress or finished, also fetch the previous day
  (`?dates=YYYYMMDD`, one day before the default day's date) so a European daytime visitor
  sees last night's finals.
- Select, in order: the game in `?game=<espnId>` if present; else the first in-progress game;
  else the most recent finished game (today's, then the previous day's); else the next
  scheduled game.
- Above the scorebar, a row of compact game chips (tricodes, score or tip-off time in the
  visitor's local time, a LIVE badge). Clicking a chip selects that game and updates `?game=`
  so the view can be shared. Every chip is selectable.
- A **scheduled** game shows the scorebar with "Tip-off hh:mm" (local time) and a short
  "not started" note in place of court, comparison and box score (ESPN returns no box score
  or plays before tip-off).
- A **finished** game shows the full layout with "Final" instead of the clock and no
  possession pill.
- No games at all: a short message and nothing else.
- Polling (owner's decision): **only if at least one game is in progress when the page
  loads.**
  - Then: scoreboard every 30 s, plus `summary` every 30 s while the selected game is in
    progress. Polling stops for good once no game is in progress any more.
  - No game in progress at load → **no polling at all**, not even the scoreboard. A selected
    scheduled game shows "Tip-off hh:mm — reload the page once it has started".
  - All polling pauses while `document.hidden`.

## Constraints

- Next.js 15 app router in `web/`, Tailwind with generated tokens, existing `AppShell`
  (add a "Live" nav item) and `sitemap.ts` (add `/live`). Code, comments and UI copy in
  English.
- The page shell is static; everything live is a client component. `useSearchParams` needs a
  `Suspense` boundary for the static build to succeed.
- Polling: see "Game selection and empty states".
- Team colours when two teams clash (same or near-identical accent; today ATL/POR,
  CHI/HOU/TOR, CLE/IND, DET/LAC, MIA/UTA):
  - **Owner's decision:** in a clashing matchup **Chicago switches to black and Utah to
    purple** (the Jazz purple, kept readable on the dark page).
  - **My call for the other pairs** (ATL/POR, HOU/TOR, CLE/IND, DET/LAC): the second team in
    alphabetical order gets the colour from the existing `resolve_pair` hue rotation in
    `hoops_lab/visuals/team_colors.py`.
  - **The logic stays in Python** (business logic lives in `hoops_lab/`, colours in the
    design system). Add the CHI/UTA alternates next to the team accents in
    `dashboard/components/theme.py`. `scripts/export_web_data.py` then writes a precomputed
    override table into `web/tokens.json`, e.g. `"teamPairOverrides": {"CHI-HOU": {"CHI":
    "#…"}, "MIA-UTA": {"UTA": "#…"}, …}`, keyed by the two tricodes sorted alphabetically and
    covering every pair that `collides()`. The web page only looks up its matchup key, with no
    colour maths in TypeScript and no hex literal in `web/` (gate).
  - TDD the override table in Python. Extend the token-artifact gate so a stale
    `teamPairOverrides` fails like stale `teamAccents` does.
  - Black on the near-black page would vanish. **Every team mark on `/live`** (shot dots,
    comparison bars, possession pill) gets a thin light outline from the existing ink tokens,
    so black stays black and still reads. Chicago's black is therefore exempt from
    `ensure_contrast` (it would otherwise be lightened to grey).
- **TDD for the logic.** All parsing and derivation lives in plain TypeScript modules under
  `web/lib/live/` with no React imports, tested first. No new dependency is required: Node 24
  runs `.ts` tests natively with `node --test` (type stripping). Test fixtures are trimmed
  real ESPN payloads stored outside the gate's scan roots (e.g. `web/tests/fixtures/`):
  game `401909903` (BOS @ ORL, final, 2026-11-01) plus a hand-made in-progress variant.
- Done means: `npm test`, `npm run typecheck`, `npm run build` green in `web/`; the full
  Python suite green (design gates included); the page checked in a real browser (my call on
  the order): work on a feature branch, push it, verify the **Vercel preview URL** on a
  finished game (and the scheduled-game state), then fast-forward `main`. If previews turn out
  disabled, verify locally with `next build && next start` and check production right after
  the push to `main`.
- A real in-progress game cannot be required before release (NBA games run roughly
  01:00–06:00 CET). Live-only behaviour (the `possession` flag, on-court tracking, polling,
  stale banner) is covered by the hand-made in-progress fixture and unit tests; a game-night
  check with a fix-up pass is a follow-up task, like the Streamlit live mode's.

## Left to the builder

- Component split, file names, exact Tailwind classes and spacing (follow the existing
  `StatTile` / `CourtZones` style; `CourtZones` already has half-court geometry to reuse or
  mirror for the full court).
- How the test runner is wired (`node --test` with `.ts` imports, or another zero-dependency
  arrangement), as long as `npm test` runs it.
- Display of DNP players (dimmed at the bottom with the reason, or omitted).
- Exact bar scaling in the comparison (percentages on a 0–100 scale, counts relative to the
  larger of the two values is the suggested default).
