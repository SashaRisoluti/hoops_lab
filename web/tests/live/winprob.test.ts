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
import type { WinProbModel } from "../../lib/live/types.ts";

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
