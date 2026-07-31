/**
 * Typed access to the dataset exported by `scripts/export_web_data.py`.
 *
 * The JSON is imported statically rather than fetched: the whole dataset is under
 * 100 KB, so Next inlines what each page actually uses at build time and the browser
 * makes no data request at all.
 */
import indexJson from "@/public/data/index.json";
import tokensJson from "@/tokens.json";

export type Team = {
  id: number;
  tricode: string;
  name: string;
  accent: string;
};

export type SiteIndex = {
  generatedAt: string;
  generatedFrom: string;
  seasons: string[];
  latestSeason: string;
  teams: Team[];
  summary: {
    seasons: number;
    teams: number;
    games: number;
    players: number;
  };
};

export type Leader = {
  playerId: number;
  name: string;
  tricode: string;
  value: number;
};

export type LeaderCategory = {
  key: string;
  label: string;
  leaders: Leader[];
};

export type Leaderboards = {
  season: string;
  minGames: number;
  minMinutes: number;
  categories: LeaderCategory[];
};

export type TeamRating = {
  id: number;
  tricode: string;
  name: string;
  wins: number;
  losses: number;
  offRating: number | null;
  defRating: number | null;
  netRating: number | null;
  pace: number | null;
  offRatingPctl: number | null;
  defRatingPctl: number | null;
  netRatingPctl: number | null;
};

export type TeamRatings = {
  season: string;
  teams: TeamRating[];
};

export type ShotZone = {
  zone: string;
  attempts: number;
  share: number;
  fgPct: number;
  pointsPerShot: number;
  isThree: boolean;
};

export type ShotZones = {
  season: string;
  minAttempts: number;
  totalAttempts: number;
  zones: ShotZone[];
};

export const siteIndex = indexJson as SiteIndex;

/** Readable franchise accents, already contrast-checked in Python. */
export const teamAccents = tokensJson.teamAccents as Record<string, string>;

/** Accent for a tricode, falling back to the interactive primary. */
export function accentFor(tricode: string): string {
  return teamAccents[tricode] ?? tokensJson.tokens.primary;
}

export async function getLeaderboards(season: string): Promise<Leaderboards> {
  return (await import(`@/public/data/leaders/${season}.json`)).default as Leaderboards;
}

export async function getTeamRatings(season: string): Promise<TeamRatings> {
  return (await import(`@/public/data/teams/${season}.json`)).default as TeamRatings;
}

export async function getShotZones(season: string): Promise<ShotZones> {
  return (await import(`@/public/data/shot-zones/${season}.json`)).default as ShotZones;
}

/** Attempt-weighted league average points per shot, the baseline the court colours against. */
export function leagueAveragePps(zones: ShotZone[]): number {
  const attempts = zones.reduce((sum, z) => sum + z.attempts, 0);
  if (attempts === 0) return 0;
  return zones.reduce((sum, z) => sum + z.pointsPerShot * z.attempts, 0) / attempts;
}
