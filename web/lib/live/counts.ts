import type { GameSummary, Play, TeamCounts } from "./types";

function tally(summary: GameSummary, keep: (p: Play) => boolean): TeamCounts {
  const counts: TeamCounts = { home: 0, away: 0 };
  for (const p of summary.plays) {
    if (!keep(p)) continue;
    if (p.teamId === summary.home.espnId) counts.home += 1;
    else if (p.teamId === summary.away.espnId) counts.away += 1;
  }
  return counts;
}

/** Team fouls in the current period; offensive, technical and turnover-flavoured fouls excluded. */
export function teamFoulsThisPeriod(summary: GameSummary): TeamCounts {
  return tally(
    summary,
    (p) => p.period === summary.period && /foul/i.test(p.type) && !/offensive|technical|turnover/i.test(p.type),
  );
}

/** Timeouts called by each team over the whole game (official/TV timeouts excluded). */
export function timeoutsUsed(summary: GameSummary): TeamCounts {
  return tally(summary, (p) => /timeout/i.test(p.type) && !/official/i.test(p.type));
}
