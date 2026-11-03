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

/**
 * Pregame point at t = 0, then one point per play (ESPN's granularity). In progress, a last
 * point at the summary's clock when it is past the last play; finished, a final point at the
 * end of the last period, 1 or 0 from the final score.
 */
export function wpSeries(summary: GameSummary, model: WinProbModel, prior: number): WpPoint[] {
  const at = (margin: number, remaining: number) =>
    homeWinProbability(model, {
      margin,
      secondsRemaining: remaining,
      priorDiff: prior,
      neutral: summary.neutralSite,
    }) ?? 0.5;
  const point = (period: number, clock: string, margin: number): WpPoint => ({
    t: elapsedSeconds(period, clock),
    home: at(margin, secondsRemaining(period, clock)),
    margin,
  });
  const pts = summary.plays.map((p) => point(p.period, p.clock, p.homeScore - p.awayScore));
  pts.sort((a, b) => a.t - b.t);
  pts.unshift({ t: 0, home: at(0, REG_SECONDS), margin: 0 });

  const margin = summary.home.score - summary.away.score;
  if (summary.state === "in") {
    const now = point(summary.period, summary.clock, margin);
    if (now.t > pts[pts.length - 1].t) pts.push(now);
  } else if (summary.state === "post") {
    const periods = Math.max(4, summary.period, ...summary.plays.map((p) => p.period));
    const home = margin > 0 ? 1 : margin < 0 ? 0 : 0.5; // a final tie is impossible
    pts.push({ t: REG_SECONDS + (periods - 4) * 300, home, margin });
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
