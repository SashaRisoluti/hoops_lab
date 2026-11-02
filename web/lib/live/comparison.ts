import type { ComparisonKey, ComparisonRow, GameSummary } from "./types";

const ROWS: { key: ComparisonKey; stat: string; pct: boolean }[] = [
  { key: "FG%", stat: "fieldGoalPct", pct: true },
  { key: "3P%", stat: "threePointFieldGoalPct", pct: true },
  { key: "REB", stat: "totalRebounds", pct: false },
  { key: "AST", stat: "assists", pct: false },
  { key: "STL", stat: "steals", pct: false },
  { key: "TO", stat: "turnovers", pct: false },
  { key: "PF", stat: "fouls", pct: false },
];

function num(raw: string | undefined): number | null {
  if (raw === undefined || raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** Away-vs-home team stat rows with bar widths (percent of each half), never NaN. */
export function teamComparison(summary: GameSummary): ComparisonRow[] {
  const stats = (id: string) => summary.boxes.find((b) => b.espnId === id)?.teamStats ?? {};
  const away = stats(summary.away.espnId);
  const home = stats(summary.home.espnId);
  return ROWS.map(({ key, stat, pct }) => {
    const a = num(away[stat]);
    const h = num(home[stat]);
    const max = Math.max(a ?? 0, h ?? 0);
    const label = (v: number | null) => (v === null ? "–" : pct ? `${v}%` : String(v));
    const width = (v: number | null) =>
      v === null ? 0 : pct ? v : max > 0 ? (v / max) * 100 : 0;
    return {
      key,
      away: a,
      home: h,
      awayLabel: label(a),
      homeLabel: label(h),
      awayWidth: width(a),
      homeWidth: width(h),
    };
  });
}
