import type {
  GameState,
  GameSummary,
  Play,
  PlayerLine,
  Scoreboard,
  ScoreboardGame,
  Side,
  StatKey,
  SummaryTeam,
  TeamBox,
} from "./types";

type Obj = Record<string, unknown>;

const TRICODES: Record<string, string> = {
  GS: "GSW",
  NO: "NOP",
  NY: "NYK",
  SA: "SAS",
  UTAH: "UTA",
  WSH: "WAS",
};

const obj = (v: unknown): Obj => (v && typeof v === "object" ? (v as Obj) : {});
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const str = (v: unknown): string => (typeof v === "string" ? v : typeof v === "number" ? String(v) : "");
const num = (v: unknown): number => {
  const n = typeof v === "number" ? v : Number.parseFloat(str(v));
  return Number.isFinite(n) ? n : 0;
};

/** Map an ESPN team abbreviation to the NBA tricode (`GS` becomes `GSW`). */
export function toNbaTricode(espnAbbr: string): string {
  return TRICODES[espnAbbr] ?? espnAbbr;
}

function parseState(v: unknown): GameState {
  return v === "in" || v === "post" ? v : "pre";
}

function parseCoordinate(v: unknown): Play["coordinate"] {
  const { x, y } = obj(v);
  // ESPN marks "no location" with huge negative sentinels (about -2.1e9).
  if (typeof x !== "number" || typeof y !== "number" || x < -1e6 || y < -1e6) return null;
  return { x, y };
}

function parsePlay(raw: unknown): Play {
  const p = obj(raw);
  const teamId = str(obj(p.team).id);
  return {
    id: str(p.id),
    seq: num(p.sequenceNumber),
    type: str(obj(p.type).text),
    text: str(p.text),
    period: num(obj(p.period).number),
    clock: str(obj(p.clock).displayValue),
    teamId: teamId || null,
    homeScore: num(p.homeScore),
    awayScore: num(p.awayScore),
    scoringPlay: p.scoringPlay === true,
    scoreValue: num(p.scoreValue),
    shootingPlay: p.shootingPlay === true,
    coordinate: parseCoordinate(p.coordinate),
    participants: arr(p.participants)
      .map((x) => str(obj(obj(x).athlete).id))
      .filter(Boolean),
  };
}

function parseSide(competitor: unknown, side: Side): SummaryTeam {
  const c = obj(competitor);
  const team = obj(c.team);
  return {
    espnId: str(team.id) || str(c.id),
    tricode: toNbaTricode(str(team.abbreviation)),
    name: str(team.displayName),
    score: num(c.score),
    side,
    hasPossession: c.possession === true,
  };
}

function parsePlayers(raw: unknown): PlayerLine[] {
  const group = obj(arr(obj(raw).statistics)[0]);
  const labels = arr(group.labels).map(str);
  return arr(group.athletes).map((a) => {
    const row = obj(a);
    const ath = obj(row.athlete);
    const didNotPlay = row.didNotPlay === true;
    const values = arr(row.stats);
    const stats: Partial<Record<StatKey, string>> = {};
    // Map by label, never by position: ESPN may reorder or add columns.
    labels.forEach((label, i) => {
      if (i < values.length) stats[label as StatKey] = str(values[i]);
    });
    return {
      athleteId: str(ath.id),
      name: str(ath.displayName),
      shortName: str(ath.shortName),
      jersey: str(ath.jersey),
      position: str(obj(ath.position).abbreviation),
      starter: row.starter === true,
      didNotPlay,
      reason: didNotPlay ? str(row.reason) || null : null,
      stats: didNotPlay ? {} : stats,
    };
  });
}

function parseBoxes(boxscore: unknown): TeamBox[] {
  const b = obj(boxscore);
  const stats = new Map<string, Record<string, string>>();
  for (const t of arr(b.teams)) {
    const o = obj(t);
    const teamStats: Record<string, string> = {};
    for (const s of arr(o.statistics)) teamStats[str(obj(s).name)] = str(obj(s).displayValue);
    stats.set(str(obj(o.team).id), teamStats);
  }
  return arr(b.players).map((p) => {
    const espnId = str(obj(obj(p).team).id);
    return { espnId, players: parsePlayers(p), teamStats: stats.get(espnId) ?? {} };
  });
}

/** Parse an ESPN `summary?event=` payload; missing fields fall back to empty values. */
export function parseSummary(raw: unknown): GameSummary {
  const root = obj(raw);
  const header = obj(root.header);
  const comp = obj(arr(header.competitions)[0]);
  const status = obj(comp.status);
  const competitors = arr(comp.competitors);
  const find = (side: Side) => competitors.find((c) => obj(c).homeAway === side);
  const plays = arr(root.plays).map(parsePlay);
  const last = plays[plays.length - 1];
  return {
    id: str(header.id) || str(comp.id),
    state: parseState(obj(status.type).state),
    period: num(status.period) || plays.reduce((m, p) => Math.max(m, p.period), 0),
    clock: str(status.displayClock) || last?.clock || "",
    statusDetail: str(obj(status.type).detail),
    home: parseSide(find("home"), "home"),
    away: parseSide(find("away"), "away"),
    boxes: parseBoxes(root.boxscore),
    plays,
    neutralSite: comp.neutralSite === true,
    seasonType: num(obj(header.season).type) || 2,
    // An entry without a finite percentage is dropped, never charted as a fake 0%.
    espnWinProbability: arr(root.winprobability).flatMap((w) => {
      const home = obj(w).homeWinPercentage;
      return typeof home === "number" && Number.isFinite(home)
        ? [{ playId: str(obj(w).playId), home }]
        : [];
    }),
  };
}

/** Parse an ESPN `scoreboard` payload; scores stay `null` until the game starts. */
export function parseScoreboard(raw: unknown): Scoreboard {
  const root = obj(raw);
  const games = arr(root.events).map((e): ScoreboardGame => {
    const ev = obj(e);
    const state = parseState(obj(obj(ev.status).type).state);
    const comp = obj(arr(ev.competitions)[0]);
    const competitors = arr(comp.competitors);
    const side = (s: Side) => {
      const c = obj(competitors.find((x) => obj(x).homeAway === s));
      return {
        tricode: toNbaTricode(str(obj(c.team).abbreviation)),
        score: state === "pre" ? null : num(c.score),
      };
    };
    return {
      id: str(ev.id),
      state,
      startTime: str(ev.date),
      statusDetail: str(obj(obj(ev.status).type).detail),
      home: side("home"),
      away: side("away"),
      neutralSite: comp.neutralSite === true,
      seasonType: num(obj(ev.season).type) || 2,
    };
  });
  return { day: str(obj(root.day).date) || null, games };
}
