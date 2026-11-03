import { test } from "node:test";
import assert from "node:assert/strict";
import {
  elapsedSeconds,
  espnSeries,
  homeWinProbability,
  priorDiff,
  secondsRemaining,
  wpAvailable,
  wpSeries,
} from "../../lib/live/winprob.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";
import type { GameState, GameSummary, Play, WinProbModel } from "../../lib/live/types.ts";

function play(over: Partial<Play>): Play {
  return {
    id: "", seq: 0, type: "", text: "", period: 1, clock: "12:00", teamId: null,
    scoringPlay: false, scoreValue: 0, shootingPlay: false, coordinate: null, participants: [],
    homeScore: 0, awayScore: 0,
    ...over,
  };
}

/** The final fixture (ORL home, not neutral) with its state, clock, score and plays replaced. */
function game(
  state: GameState,
  period: number,
  clock: string,
  [home, away]: [number, number],
  plays: Play[],
): GameSummary {
  const g = structuredClone(parseSummary(fixture("espn-summary-final.json")));
  Object.assign(g, { state, period, clock, plays });
  g.home.score = home;
  g.away.score = away;
  return g;
}

const model: WinProbModel = {
  available: true,
  coefficients: { a: 0.1, b: 0.3, c: 0.05 },
  teams: { ORL: 2, BOS: -2 },
};
const near = (a: number | null, b: number) => {
  assert.ok(a !== null && Math.abs(a - b) < 1e-6, `${a} != ${b}`);
};

test("homeWinProbability matches hand-computed values", () => {
  const x = { margin: 6, secondsRemaining: 720, priorDiff: 4, neutral: false };
  near(homeWinProbability(model, x), 0.809998);
  near(homeWinProbability(model, { ...x, neutral: true }), 0.785835);
  near(homeWinProbability(model, { margin: 0, secondsRemaining: 2880, priorDiff: 4, neutral: false }), 0.622459);
  near(homeWinProbability(model, { margin: 1, secondsRemaining: 0, priorDiff: 4, neutral: false }), 0.995394);
  assert.equal(homeWinProbability({ available: false }, x), null);
});

test("priorDiff", () => {
  assert.equal(priorDiff(model, "ORL", "BOS"), 4);
  assert.equal(priorDiff(model, "ORL", "XXX"), null);
  assert.equal(priorDiff({ available: false }, "ORL", "BOS"), null);
});

test("clocks", () => {
  assert.equal(elapsedSeconds(1, "12:00"), 0);
  assert.equal(elapsedSeconds(2, "5:30"), 1110);
  assert.equal(elapsedSeconds(4, "0.0"), 2880);
  near(elapsedSeconds(4, "9.1"), 2870.9);
  assert.equal(elapsedSeconds(5, "4:58"), 2882);
  assert.equal(secondsRemaining(3, "4:58"), 1018);
  assert.equal(secondsRemaining(5, "4:58"), 298);
});

test("wpSeries on the final fixture", () => {
  const s = parseSummary(fixture("espn-summary-final.json"));
  const pts = wpSeries(s, model, 4);
  assert.equal(pts[0].t, 0);
  assert.equal(pts[0].margin, 0);
  const last = pts[pts.length - 1];
  assert.equal(last.margin, -11);
  assert.equal(last.home, 0);
  for (let i = 1; i < pts.length; i++) assert.ok(pts[i].t >= pts[i - 1].t);
  const margins = new Set(s.plays.map((p) => p.homeScore - p.awayScore));
  for (const p of pts.slice(1)) assert.ok(margins.has(p.margin));
});

test("wpSeries on the live fixture", () => {
  const s = parseSummary(fixture("espn-summary-live.json"));
  const last = wpSeries(s, model, 4).at(-1)!;
  assert.equal(last.margin, -10);
  assert.ok(last.home > 0 && last.home < 1);
});

test("wpSeries has one point per play, scoring or not", () => {
  const plays = [
    play({ clock: "11:30" }),
    play({ clock: "11:00", homeScore: 2 }),
    play({ clock: "10:40", homeScore: 2 }), // a rebound: same score, still a point
  ];
  const pts = wpSeries(game("in", 1, "10:40", [2, 0], plays), model, 4);
  assert.deepEqual(
    pts.map((p) => [p.t, p.margin]),
    [[0, 0], [30, 0], [60, 2], [80, 2]],
  );
  near(pts[0].home, 0.622459);
  near(pts[1].home, 0.621846);
  near(pts[2].home, 0.667496);
  near(pts[3].home, 0.667266);
});

test("wpSeries of a game in progress ends at the summary's clock", () => {
  const plays = [play({ period: 2, clock: "5:00", homeScore: 50, awayScore: 44 })];
  const last = wpSeries(game("in", 2, "3:12", [52, 44], plays), model, 4).at(-1)!;
  assert.equal(last.t, 1248);
  assert.equal(last.margin, 8);
  near(last.home, 0.808319); // 1632 s left
});

test("wpSeries of a finished game ends at the final horn, 1 or 0 from the final score", () => {
  const plays = [play({ period: 4, clock: "0:45", homeScore: 100, awayScore: 98 })];
  const won = wpSeries(game("post", 4, "0.0", [100, 98], plays), model, 4);
  assert.equal(won.length, 3);
  assert.deepEqual(won.at(-1), { t: 2880, home: 1, margin: 2 });
  const lost = wpSeries(game("post", 4, "0.0", [98, 100], plays), model, 4).at(-1)!;
  assert.deepEqual(lost, { t: 2880, home: 0, margin: -2 });
  const tied = wpSeries(game("post", 4, "0.0", [100, 100], plays), model, 4).at(-1)!;
  assert.equal(tied.home, 0.5);
});

test("wpSeries through a tied end of regulation into overtime", () => {
  const plays = [
    play({ period: 4, clock: "0.0", homeScore: 100, awayScore: 100 }),
    play({ period: 5, clock: "2:30", homeScore: 102, awayScore: 100 }),
  ];
  const pts = wpSeries(game("post", 5, "0.0", [105, 103], plays), model, 4);
  assert.deepEqual(
    pts.map((p) => [p.t, p.margin]),
    [[0, 0], [2880, 0], [3030, 2], [3180, 2]],
  );
  near(pts[1].home, 0.502329); // tied at the horn: the 1-second floor leaves ~50%
  near(pts[2].home, 0.72918); // 150 s left in OT
  assert.equal(pts[3].home, 1);

  const twoOt = game("post", 6, "0.0", [110, 112], [...plays, play({ period: 6, clock: "1:00" })]);
  assert.deepEqual(wpSeries(twoOt, model, 4).at(-1), { t: 3480, home: 0, margin: -2 });
});

test("espnSeries drops unknown ids", () => {
  const s = parseSummary(fixture("espn-summary-final.json"));
  const [a, b] = [s.plays[3], s.plays[10]];
  s.espnWinProbability = [
    { playId: a.id, home: 0.4 },
    { playId: "nope", home: 0.5 },
    { playId: b.id, home: 0.6 },
  ];
  const pts = espnSeries(s);
  assert.equal(pts.length, 2);
  assert.equal(pts[0].t, elapsedSeconds(a.period, a.clock));
  assert.equal(pts[1].home, 0.6);
});

test("wpAvailable", () => {
  assert.equal(wpAvailable(model, 1, 4), false);
  assert.equal(wpAvailable(model, 2, null), false);
  assert.equal(wpAvailable({ available: false }, 2, 4), false);
  assert.equal(wpAvailable(model, 2, 4), true);
});
