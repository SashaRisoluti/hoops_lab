import type { GameSummary } from "./types";

/** Period number → `Q1`–`Q4`, `OT`, `2OT`, ... */
export function periodLabel(period: number): string {
  if (period <= 4) return `Q${period}`;
  return period === 5 ? "OT" : `${period - 4}OT`;
}

/**
 * Scoreboard clock text: `Q3 · 4:58` live, `Final`, or `Scheduled`. Between periods the
 * clock reads `0.0`, so ESPN's status text (`Halftime`, `End of 3rd Quarter`) is shown.
 */
export function clockLabel(summary: GameSummary): string {
  if (summary.state === "post") return "Final";
  if (summary.state === "pre") return "Scheduled";
  if ((summary.clock === "0.0" || !summary.clock) && summary.statusDetail) return summary.statusDetail;
  return `${periodLabel(summary.period)} · ${summary.clock}`;
}

/** 24-hour tip-off time in the given zone (default: the runtime's); `–` for a bad date. */
export function tipOffLabel(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "–";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone,
  }).format(date);
}

/** Text of the most recent play, or `null` when there are none. */
export function lastPlayText(summary: GameSummary): string | null {
  const last = summary.plays[summary.plays.length - 1];
  return last ? last.text : null;
}
