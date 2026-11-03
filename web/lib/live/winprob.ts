import type { EspnWpPoint, GameSummary, WinProbModel, WpPoint } from "./types";

const REG_SECONDS = 2880;

/** ESPN clock ("12:00", "5:30", "9.1") to seconds. */
function clockSeconds(clock: string): number {
  const [m, s] = clock.includes(":") ? clock.split(":") : ["0", clock];
  return Number(m) * 60 + Number(s);
}

/** Elapsed game seconds; quarters are 720 s, overtimes 300 s. */
export function elapsedSeconds(period: number, clock: string): number {
  const left = clockSeconds(clock);
  if (period <= 4) return period * 720 - left;
  return REG_SECONDS + (period - 4) * 300 - left;
}

/** Seconds left in regulation, or in the current overtime. */
export function secondsRemaining(period: number, clock: string): number {
  return period <= 4 ? REG_SECONDS - elapsedSeconds(period, clock) : clockSeconds(clock);
}

/** Home win probability; `null` when the model is unavailable. */
export function homeWinProbability(
  model: WinProbModel,
  x: { margin: number; secondsRemaining: number; priorDiff: number; neutral: boolean },
): number | null {
  if (!model.available || !model.coefficients) return null;
  const { a, b, c } = model.coefficients;
  const f = Math.max(x.secondsRemaining, 1) / REG_SECONDS;
  const r = Math.sqrt(f);
  const z = (a * x.margin) / r + b * r * (x.neutral ? 0 : 1) + c * x.priorDiff * r;
  return 1 / (1 + Math.exp(-z));
}

/** Pregame net-rating difference (home − away); `null` if either team is unknown. */
export function priorDiff(model: WinProbModel, homeTricode: string, awayTricode: string): number | null {
  const h = model.teams?.[homeTricode];
  const a = model.teams?.[awayTricode];
  return h === undefined || a === undefined ? null : h - a;
}

export function wpAvailable(model: WinProbModel, seasonType: number, prior: number | null): boolean {
  return model.available && seasonType !== 1 && prior !== null;
}

/** Pregame point plus one point per score change; a finished game ends at 1 or 0. */
export function wpSeries(summary: GameSummary, model: WinProbModel, prior: number): WpPoint[] {
  const at = (margin: number, remaining: number) =>
    homeWinProbability(model, {
      margin,
      secondsRemaining: remaining,
      priorDiff: prior,
      neutral: summary.neutralSite,
    }) ?? 0.5;
  const pts: WpPoint[] = [{ t: 0, home: at(0, REG_SECONDS), margin: 0 }];
  let prevHome = 0;
  let prevAway = 0;
  for (const p of summary.plays) {
    if (p.homeScore === prevHome && p.awayScore === prevAway) continue;
    prevHome = p.homeScore;
    prevAway = p.awayScore;
    const margin = p.homeScore - p.awayScore;
    pts.push({
      t: elapsedSeconds(p.period, p.clock),
      home: at(margin, secondsRemaining(p.period, p.clock)),
      margin,
    });
  }
  pts.sort((a, b) => a.t - b.t);
  if (summary.state === "post" && pts.length > 1) {
    const last = pts[pts.length - 1];
    last.home = last.margin > 0 ? 1 : 0;
  }
  return pts;
}

/** ESPN's benchmark curve placed on our time axis; ids without a matching play are dropped. */
export function espnSeries(summary: GameSummary): EspnWpPoint[] {
  const plays = new Map(summary.plays.map((p) => [p.id, p]));
  const out: EspnWpPoint[] = [];
  for (const e of summary.espnWinProbability) {
    const p = plays.get(e.playId);
    if (p) out.push({ t: elapsedSeconds(p.period, p.clock), home: e.home });
  }
  return out;
}
