import { parseScoreboard, parseSummary } from "./espn";
import type { GameSummary, Scoreboard } from "./types";

const BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba";

async function getJson(url: string): Promise<unknown> {
  const res = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
  if (!res.ok) throw new Error(`ESPN responded ${res.status}`);
  return res.json();
}

/** Scoreboard for ESPN's default day, or for `dates` (`YYYYMMDD`). */
export async function fetchScoreboard(dates?: string): Promise<Scoreboard> {
  return parseScoreboard(await getJson(`${BASE}/scoreboard${dates ? `?dates=${dates}` : ""}`));
}

export async function fetchSummary(id: string): Promise<GameSummary> {
  return parseSummary(await getJson(`${BASE}/summary?event=${encodeURIComponent(id)}`));
}
