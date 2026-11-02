import type { CourtShot, GameSummary } from "./types";

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** The last `n` field-goal attempts placed on a 94x50 ft court (home attacks right), oldest first. */
export function lastShots(summary: GameSummary, n = 10): CourtShot[] {
  const shots: CourtShot[] = [];
  for (const p of summary.plays) {
    if (!p.shootingPlay || /Free Throw/i.test(p.type) || p.coordinate === null) continue;
    const { x, y } = p.coordinate;
    const home = p.teamId === summary.home.espnId;
    if (!home && p.teamId !== summary.away.espnId) continue;
    shots.push({
      courtX: clamp(home ? 88.75 - y : 5.25 + y, 0, 94),
      courtY: home ? x : 50 - x,
      made: p.scoringPlay,
      side: home ? "home" : "away",
      text: p.text,
    });
  }
  return shots.slice(-n);
}
