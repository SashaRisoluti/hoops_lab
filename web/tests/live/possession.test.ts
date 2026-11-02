import { test } from "node:test";
import assert from "node:assert/strict";
import { possession } from "../../lib/live/possession.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import type { GameSummary, Play } from "../../lib/live/types.ts";
import { fixture } from "../load.ts";

const H = "19";
const A = "2";

function play(over: Partial<Play>): Play {
  return {
    seq: 99999, type: "", text: "", period: 3, clock: "1:00", teamId: null,
    scoringPlay: false, scoreValue: 0, shootingPlay: false, coordinate: null, participants: [],
    ...over,
  };
}

/** Live summary with both flags cleared and `plays` replaced. */
function bare(plays: Play[]): GameSummary {
  const g = structuredClone(parseSummary(fixture("espn-summary-live.json")));
  g.home.hasPossession = false;
  g.away.hasPossession = false;
  g.plays = plays;
  return g;
}

test("possession: the flag wins", () => {
  const g = parseSummary(fixture("espn-summary-live.json"));
  assert.equal(possession(g), "away");
  const flipped = structuredClone(g);
  flipped.away.hasPossession = false;
  flipped.home.hasPossession = true;
  assert.equal(possession(flipped), "home");
});

test("possession: inferred from plays when no flag", () => {
  const g = structuredClone(parseSummary(fixture("espn-summary-live.json")));
  g.away.hasPossession = false;
  assert.equal(possession(g), "away");
});

test("possession: final game ends with null", () => {
  assert.equal(possession(parseSummary(fixture("espn-summary-final.json"))), null);
});

const cases: [string, Partial<Play>[], "home" | "away" | null][] = [
  ["defensive rebound", [{ type: "Defensive Rebound", teamId: H }], "home"],
  ["turnover", [{ type: "Lost Ball Turnover", teamId: H }], "away"],
  ["made shot", [{ type: "Jump Shot", teamId: A, shootingPlay: true, scoringPlay: true }], "home"],
  [
    "first of two FTs made",
    [{ type: "Defensive Rebound", teamId: A }, { type: "Free Throw - 1 of 2", teamId: H, scoringPlay: true, shootingPlay: true }],
    "away",
  ],
  ["last FT made", [{ type: "Free Throw - 2 of 2", teamId: H, scoringPlay: true, shootingPlay: true }], "away"],
  [
    "last FT missed",
    [{ type: "Defensive Rebound", teamId: H }, { type: "Free Throw - 2 of 2", teamId: H, shootingPlay: true }],
    "home",
  ],
  ["last FT of 1 made", [{ type: "Free Throw - 1 of 1", teamId: H, scoringPlay: true, shootingPlay: true }], "away"],
  [
    "technical FT made by the team with the ball",
    [{ type: "Defensive Rebound", teamId: A }, { type: "Free Throw - Technical", teamId: A, scoringPlay: true, shootingPlay: true }],
    "away",
  ],
  [
    "technical FT made by the defence",
    [{ type: "Defensive Rebound", teamId: A }, { type: "Free Throw - Technical", teamId: H, scoringPlay: true, shootingPlay: true }],
    "away",
  ],
  [
    "last flagrant FT made: shooting team keeps the ball",
    [{ type: "Defensive Rebound", teamId: H }, { type: "Free Throw - Flagrant 2 of 2", teamId: H, scoringPlay: true, shootingPlay: true }],
    "home",
  ],
  ["jump ball", [{ type: "Jumpball", teamId: H }], "home"],
  ["end of period", [{ type: "Defensive Rebound", teamId: H }, { type: "End Period" }], null],
  [
    "neutral plays",
    [
      { type: "Defensive Rebound", teamId: H },
      { type: "Jump Shot", teamId: H, shootingPlay: true },
      { type: "Personal Foul", teamId: A },
      { type: "Full Timeout", teamId: A },
      { type: "Substitution", teamId: A, participants: ["1", "2"] },
    ],
    "home",
  ],
];

for (const [name, plays, want] of cases) {
  test(`possession inference: ${name}`, () => {
    assert.equal(possession(bare(plays.map((p) => play(p)))), want);
  });
}
