import type { ScoreboardGame } from "./types";

/** True when today's board has no game in progress or finished (so yesterday's games are worth loading). */
export function needsPreviousDay(today: ScoreboardGame[]): boolean {
  return !today.some((g) => g.state === "in" || g.state === "post");
}

/** `"YYYY-MM-DD"` → the previous day as `"YYYYMMDD"` (UTC arithmetic). */
export function previousDayParam(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10).replaceAll("-", "");
}

const byStart = (a: ScoreboardGame, b: ScoreboardGame) => a.startTime.localeCompare(b.startTime);

/**
 * Choose the game to show: the requested id if it exists, else a live game, else the latest
 * final (today first, then yesterday), else the earliest scheduled game, else `null`.
 */
export function pickGame(
  today: ScoreboardGame[],
  previous: ScoreboardGame[],
  requested: string | null,
): string | null {
  const all = [...today, ...previous];
  if (requested && all.some((g) => g.id === requested)) return requested;
  const live = today.filter((g) => g.state === "in").sort(byStart);
  if (live.length) return live[0].id;
  for (const pool of [today, previous]) {
    const finals = pool.filter((g) => g.state === "post").sort(byStart);
    if (finals.length) return finals[finals.length - 1].id;
  }
  const upcoming = today.filter((g) => g.state === "pre").sort(byStart);
  return upcoming.length ? upcoming[0].id : null;
}

/** Poll only while at least one game is in progress. */
export function shouldPoll(games: ScoreboardGame[]): boolean {
  return games.some((g) => g.state === "in");
}
