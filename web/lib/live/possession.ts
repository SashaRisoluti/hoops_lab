import type { GameSummary, Side } from "./types";

/**
 * Side with the ball: ESPN's possession flag when set, otherwise inferred by replaying the
 * plays (rebound, turnover, made shot, last made free throw, jump ball; period/game end clears it).
 * Only a plain "Free Throw - N of M" hands the ball over: technical, flagrant and other
 * special free throws leave possession where it was.
 */
export function possession(summary: GameSummary): Side | null {
  if (summary.home.hasPossession) return "home";
  if (summary.away.hasPossession) return "away";

  const sideOf = (teamId: string | null): Side | null =>
    teamId === summary.home.espnId ? "home" : teamId === summary.away.espnId ? "away" : null;
  const other = (s: Side | null): Side | null => (s === "home" ? "away" : s === "away" ? "home" : null);

  let current: Side | null = null;
  for (const p of summary.plays) {
    const side = sideOf(p.teamId);
    if (/^End (Period|Game)$/.test(p.type)) current = null;
    else if (/Rebound/.test(p.type) || p.type === "Jumpball") current = side ?? current;
    else if (/Turnover/.test(p.type)) current = other(side) ?? current;
    else if (p.type.startsWith("Free Throw")) {
      const ft = /^Free Throw - (\d) of (\d)$/.exec(p.type);
      if (ft && p.scoringPlay && ft[1] === ft[2]) current = other(side) ?? current;
    } else if (p.shootingPlay && p.scoringPlay) current = other(side) ?? current;
  }
  return current;
}
