/**
 * Shapes of the live game data, as parsed from the ESPN public API and derived from it.
 *
 * Every module under `lib/live/` imports from here with `import type` only, so the
 * Node test runner never has to resolve a runtime import between them.
 */

export type GameState = "pre" | "in" | "post";
export type Side = "home" | "away";
export type StatKey =
  | "MIN"
  | "PTS"
  | "FG"
  | "3PT"
  | "FT"
  | "REB"
  | "AST"
  | "TO"
  | "STL"
  | "BLK"
  | "OREB"
  | "DREB"
  | "PF"
  | "+/-";

export type SummaryTeam = {
  espnId: string;
  /** NBA tricode (ESPN abbreviations such as `GS` are mapped to `GSW`). */
  tricode: string;
  name: string;
  score: number;
  side: Side;
  hasPossession: boolean;
};

export type Play = {
  /** ESPN play id; `winprobability` entries reference it as `playId`. */
  id: string;
  seq: number;
  type: string;
  text: string;
  period: number;
  clock: string;
  teamId: string | null;
  scoringPlay: boolean;
  scoreValue: number;
  shootingPlay: boolean;
  /** Feet in the shooting team's half court, hoop near (25, 0); `null` for non-shots. */
  coordinate: { x: number; y: number } | null;
  /** Athlete ids; for a substitution `[entering, leaving]`. */
  participants: string[];
  /** Running score after the play. */
  homeScore: number;
  awayScore: number;
};

export type PlayerLine = {
  athleteId: string;
  name: string;
  shortName: string;
  jersey: string;
  position: string;
  starter: boolean;
  didNotPlay: boolean;
  reason: string | null;
  stats: Partial<Record<StatKey, string>>;
};

export type TeamBox = {
  espnId: string;
  players: PlayerLine[];
  /** ESPN team statistics, `name` → `displayValue`. */
  teamStats: Record<string, string>;
};

export type GameSummary = {
  id: string;
  state: GameState;
  period: number;
  clock: string;
  statusDetail: string;
  home: SummaryTeam;
  away: SummaryTeam;
  boxes: TeamBox[];
  plays: Play[];
  neutralSite: boolean;
  /** ESPN season type: 1 preseason, 2 regular season, 3 postseason, 5 play-in. */
  seasonType: number;
  /** ESPN's own home win probability per play (0–1), the benchmark line. */
  espnWinProbability: { playId: string; home: number }[];
};

export type ScoreboardGame = {
  id: string;
  state: GameState;
  startTime: string;
  statusDetail: string;
  home: { tricode: string; score: number | null };
  away: { tricode: string; score: number | null };
  neutralSite: boolean;
  /** ESPN season type: 1 preseason, 2 regular season, 3 postseason, 5 play-in. */
  seasonType: number;
};

export type Scoreboard = { day: string | null; games: ScoreboardGame[] };

/** A point of our win-probability curve: elapsed game seconds, home win probability, home − away. */
export type WpPoint = { t: number; home: number; margin: number };

/** A point of ESPN's benchmark curve, placed at its play's elapsed time. */
export type EspnWpPoint = { t: number; home: number };

/**
 * `web/public/data/win-probability.json`, written by `scripts/export_web_data.py`.
 * `available: false` (gate failed or not exported yet) carries no coefficients.
 */
export type WinProbModel = {
  available: boolean;
  coefficients?: { a: number; b: number; c: number };
  homeCourtPts?: number;
  pointsPerNetRating?: number;
  scale?: number;
  k?: number;
  season?: string;
  asOf?: string;
  /** NBA tricode → pregame net rating. */
  teams?: Record<string, number>;
  metrics?: {
    trainGames: number;
    holdoutGames: number;
    holdoutLogLoss: number;
    baselineLogLoss: number;
    ece: number;
    pregameLogLoss: number;
    constantLogLoss: number;
  };
};

export type TeamCounts = { home: number; away: number };

/** A shot placed on a full court in feet: `courtX` 0–94 along the length, `courtY` 0–50 across. */
export type CourtShot = { courtX: number; courtY: number; made: boolean; side: Side; text: string };

export type ComparisonKey = "FG%" | "3P%" | "REB" | "AST" | "STL" | "TO" | "PF";

export type ComparisonRow = {
  key: ComparisonKey;
  away: number | null;
  home: number | null;
  awayLabel: string;
  homeLabel: string;
  /** Bar widths as a percentage of their half, 0–100. */
  awayWidth: number;
  homeWidth: number;
};

export type BoxColumn =
  | "MIN"
  | "PTS"
  | "REB"
  | "AST"
  | "STL"
  | "BLK"
  | "TO"
  | "PF"
  | "FG"
  | "3PT"
  | "FT"
  | "+/-";

export type BoxRow = {
  athleteId: string;
  name: string;
  onCourt: boolean;
  didNotPlay: boolean;
  reason: string | null;
  foulTrouble: boolean;
  cells: Record<BoxColumn, string>;
};
