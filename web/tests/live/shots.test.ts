import { test } from "node:test";
import assert from "node:assert/strict";
import { lastShots } from "../../lib/live/shots.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";
import type { GameSummary, Play } from "../../lib/live/types.ts";

function shot(teamId: string, x: number, y: number, extra: Partial<Play> = {}): Play {
  return {
    id: "", homeScore: 0, awayScore: 0,
    seq: 1, type: "Jump Shot", text: "shot", period: 1, clock: "1:00", teamId,
    scoringPlay: false, scoreValue: 0, shootingPlay: true, coordinate: { x, y }, participants: [],
    ...extra,
  };
}

function withPlays(plays: Play[]): GameSummary {
  const g = structuredClone(parseSummary(fixture("espn-summary-final.json")));
  g.plays = plays;
  return g;
}

test("final game: last 10 shots, chronological", () => {
  const shots = lastShots(parseSummary(fixture("espn-summary-final.json")));
  assert.equal(shots.length, 10);
  assert.deepEqual(
    shots.map((s) => s.made),
    [false, true, false, false, false, true, false, false, true, false],
  );
});

test("free throws and shots without coordinates are skipped", () => {
  const shots = lastShots(
    withPlays([
      shot("19", 25, 5, { type: "Free Throw - 1 of 2", text: "makes free throw 1 of 2" }),
      shot("19", 25, 5, { coordinate: null }),
      shot("19", 25, 5, { shootingPlay: false }),
    ]),
  );
  assert.deepEqual(shots, []);
});

test("court mapping", () => {
  const [a, b, c, d] = lastShots(
    withPlays([
      shot("19", 25, 0, { text: "a" }),
      shot("2", 25, 0, { text: "b" }),
      shot("19", 2, 1, { text: "c", scoringPlay: true }),
      shot("19", 25, 95, { text: "d" }),
    ]),
  );
  assert.deepEqual(a, { courtX: 88.75, courtY: 25, made: false, side: "home", text: "a" });
  assert.deepEqual(b, { courtX: 5.25, courtY: 25, made: false, side: "away", text: "b" });
  assert.equal(c.courtX, 87.75);
  assert.equal(c.courtY, 2);
  assert.equal(c.made, true);
  assert.equal(d.courtX, 0);
});
