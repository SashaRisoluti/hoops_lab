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
};

export type ScoreboardGame = {
  id: string;
  state: GameState;
  startTime: string;
  statusDetail: string;
  home: { tricode: string; score: number | null };
  away: { tricode: string; score: number | null };
};

export type Scoreboard = { day: string | null; games: ScoreboardGame[] };

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
