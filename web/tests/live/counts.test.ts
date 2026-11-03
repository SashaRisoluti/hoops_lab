import { test } from "node:test";
import assert from "node:assert/strict";
import { teamFoulsThisPeriod, timeoutsUsed } from "../../lib/live/counts.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";
import type { GameSummary, Play } from "../../lib/live/types.ts";

const final = () => parseSummary(fixture("espn-summary-final.json"));
const live = () => parseSummary(fixture("espn-summary-live.json"));

function withPlay(g: GameSummary, p: Partial<Play>): GameSummary {
  const c = structuredClone(g);
  c.plays.push({
    id: "", homeScore: 0, awayScore: 0,
    seq: 99999, type: "", text: "", period: c.period, clock: "1:00", teamId: "19",
    scoringPlay: false, scoreValue: 0, shootingPlay: false, coordinate: null, participants: [],
    ...p,
  });
  return c;
}

test("fixtures: fouls this period", () => {
  assert.deepEqual(teamFoulsThisPeriod(final()), { home: 4, away: 4 });
  assert.deepEqual(teamFoulsThisPeriod(live()), { home: 3, away: 4 });
});

test("fixtures: timeouts used", () => {
  assert.deepEqual(timeoutsUsed(final()), { home: 6, away: 5 });
  assert.deepEqual(timeoutsUsed(live()), { home: 3, away: 2 });
});

test("non-team fouls are not counted, loose ball fouls are", () => {
  const base = final();
  const before = teamFoulsThisPeriod(base);
  for (const type of ["Offensive Foul", "Technical Foul", "Offensive Foul Turnover"]) {
    assert.deepEqual(teamFoulsThisPeriod(withPlay(base, { type })), before, type);
  }
  const after = teamFoulsThisPeriod(withPlay(base, { type: "Loose Ball Foul" }));
  assert.equal(after.home, before.home + 1);
  assert.equal(after.away, before.away);
});

test("a foul in an earlier period is not counted", () => {
  const base = final();
  assert.deepEqual(
    teamFoulsThisPeriod(withPlay(base, { type: "Personal Foul", period: 1 })),
    teamFoulsThisPeriod(base),
  );
});

test("overtime counts only period-5 fouls", () => {
  const ot = structuredClone(final());
  ot.period = 5;
  assert.deepEqual(teamFoulsThisPeriod(ot), { home: 0, away: 0 });
  const g = withPlay(ot, { type: "Personal Foul", teamId: "2" });
  assert.deepEqual(teamFoulsThisPeriod(g), { home: 0, away: 1 });
});

test("official timeouts and unknown teams are ignored", () => {
  const base = final();
  const before = timeoutsUsed(base);
  assert.deepEqual(timeoutsUsed(withPlay(base, { type: "Official Timeout" })), before);
  assert.deepEqual(timeoutsUsed(withPlay(base, { type: "Full Timeout", teamId: null })), before);
  assert.equal(timeoutsUsed(withPlay(base, { type: "Full Timeout", teamId: "2" })).away, before.away + 1);
});
