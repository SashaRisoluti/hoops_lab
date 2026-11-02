import type { BoxColumn, BoxRow, PlayerLine, TeamBox } from "./types";

/** Box score columns, in display order. */
export const BOX_COLUMNS: readonly BoxColumn[] = [
  "MIN", "PTS", "REB", "AST", "STL", "BLK", "TO", "PF", "FG", "3PT", "FT", "+/-",
];

function cells(p: PlayerLine): Record<BoxColumn, string> {
  const out = {} as Record<BoxColumn, string>;
  for (const c of BOX_COLUMNS) out[c] = p.didNotPlay ? "" : (p.stats[c] ?? "");
  return out;
}

/** Rows ordered on court, then bench, then did-not-play (box order within each group). */
export function boxRows(box: TeamBox, onCourtIds: string[]): BoxRow[] {
  const rank = (p: PlayerLine) => (p.didNotPlay ? 2 : onCourtIds.includes(p.athleteId) ? 0 : 1);
  return box.players
    .map((p, i) => ({ p, i }))
    .sort((a, b) => rank(a.p) - rank(b.p) || a.i - b.i)
    .map(({ p }) => {
      const pf = p.didNotPlay ? 0 : Number(p.stats.PF);
      return {
        athleteId: p.athleteId,
        name: p.name,
        onCourt: !p.didNotPlay && onCourtIds.includes(p.athleteId),
        didNotPlay: p.didNotPlay,
        reason: p.didNotPlay ? p.reason : null,
        foulTrouble: pf >= 5,
        cells: cells(p),
      };
    });
}

/** Team totals row; shooting splits come from the team "made-attempted" stats. */
export function boxTotals(box: TeamBox, score: number): Record<BoxColumn, string> {
  const t = box.teamStats;
  return {
    MIN: "",
    PTS: String(score),
    REB: t.totalRebounds ?? "",
    AST: t.assists ?? "",
    STL: t.steals ?? "",
    BLK: t.blocks ?? "",
    TO: t.turnovers ?? "",
    PF: t.fouls ?? "",
    FG: t["fieldGoalsMade-fieldGoalsAttempted"] ?? "",
    "3PT": t["threePointFieldGoalsMade-threePointFieldGoalsAttempted"] ?? "",
    FT: t["freeThrowsMade-freeThrowsAttempted"] ?? "",
    "+/-": "",
  };
}
