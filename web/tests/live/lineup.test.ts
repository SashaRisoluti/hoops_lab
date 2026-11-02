import { test } from "node:test";
import assert from "node:assert/strict";
import { onCourt } from "../../lib/live/lineup.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import type { Play } from "../../lib/live/types.ts";
import { fixture } from "../load.ts";

const sorted = (ids: string[]) => [...ids].sort();

function play(over: Partial<Play>): Play {
  return {
    seq: 99999, type: "", text: "", period: 4, clock: "0:00", teamId: null,
    scoringPlay: false, scoreValue: 0, shootingPlay: false, coordinate: null, participants: [],
    ...over,
  };
}

test("onCourt final game", () => {
  const c = onCourt(parseSummary(fixture("espn-summary-final.json")));
  assert.deepEqual(sorted(c.home), ["4066320", "4277847", "4566434", "4702382", "4712849"]);
  assert.deepEqual(sorted(c.away), ["3078576", "4397424", "4593841", "4683689", "5175647"]);
});

test("onCourt live game", () => {
  const c = onCourt(parseSummary(fixture("espn-summary-live.json")));
  assert.deepEqual(sorted(c.home), ["4066320", "4277847", "4566434", "4702382", "5239561"]);
  assert.deepEqual(sorted(c.away), ["4065648", "4065804", "4066354", "4397424", "4683689"]);
});

test("onCourt ignores malformed substitutions and does not mutate", () => {
  const g = parseSummary(fixture("espn-summary-final.json"));
  const before = onCourt(g);
  g.plays.push(
    play({ type: "Substitution", teamId: "19", participants: [] }),
    play({ type: "Substitution", teamId: "999", participants: ["1", "2"] }),
    play({ type: "Substitution", teamId: "19", participants: ["1", "not-on-court"] }),
  );
  const n = g.plays.length;
  assert.deepEqual(onCourt(g), before);
  assert.equal(g.plays.length, n);
});

test("onCourt of a pre game is empty", () => {
  assert.deepEqual(onCourt(parseSummary(fixture("espn-summary-pre.json"))), { home: [], away: [] });
});
