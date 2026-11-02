import { test } from "node:test";
import assert from "node:assert/strict";
import { parseScoreboard } from "../../lib/live/espn.ts";
import { needsPreviousDay, pickGame, previousDayParam, shouldPoll } from "../../lib/live/selection.ts";
import type { ScoreboardGame } from "../../lib/live/types.ts";
import { fixture } from "../load.ts";

const today = parseScoreboard(fixture("espn-scoreboard-today.json")).games;
const prev = parseScoreboard(fixture("espn-scoreboard-2026-11-01.json")).games;

const game = (id: string, state: ScoreboardGame["state"], startTime: string): ScoreboardGame => ({
  id,
  state,
  startTime,
  statusDetail: "",
  home: { tricode: "BOS", score: null },
  away: { tricode: "ORL", score: null },
});

test("needsPreviousDay", () => {
  assert.equal(needsPreviousDay(today), true);
  assert.equal(needsPreviousDay(prev), false);
});

test("previousDayParam", () => {
  assert.equal(previousDayParam("2026-11-02"), "20261101");
  assert.equal(previousDayParam("2026-03-01"), "20260228");
  assert.equal(previousDayParam("2027-01-01"), "20261231");
});

test("pickGame", () => {
  assert.equal(pickGame(today, prev, "401909904"), "401909904");
  assert.equal(pickGame(today, prev, "nope"), "401909906");
  const live = [game("a", "pre", "2026-11-02T23:00Z"), game("b", "in", "2026-11-02T20:00Z")];
  assert.equal(pickGame(live, prev, null), "b");
  const finals = [game("f1", "post", "2026-11-02T17:00Z"), game("f2", "post", "2026-11-02T19:00Z"), game("s", "pre", "2026-11-02T23:00Z")];
  assert.equal(pickGame(finals, prev, null), "f2");
  assert.equal(pickGame(today, [], null), "401909907");
  assert.equal(pickGame([], [], null), null);
});

test("shouldPoll", () => {
  assert.equal(shouldPoll(today), false);
  assert.equal(shouldPoll(prev), false);
  assert.equal(shouldPoll([game("b", "in", "2026-11-02T20:00Z")]), true);
});
