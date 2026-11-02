import { test } from "node:test";
import assert from "node:assert/strict";
import { teamComparison } from "../../lib/live/comparison.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";

const near = (a: number, b: number) => assert.ok(Math.abs(a - b) < 0.01, `${a} != ${b}`);

test("teamComparison on the final game", () => {
  const rows = teamComparison(parseSummary(fixture("espn-summary-final.json")));
  assert.deepEqual(rows.map((r) => r.key), ["FG%", "3P%", "REB", "AST", "STL", "TO", "PF"]);
  const by = Object.fromEntries(rows.map((r) => [r.key, r]));
  assert.deepEqual([by["FG%"].away, by["FG%"].home, by["FG%"].awayWidth, by["FG%"].homeWidth], [44, 42, 44, 42]);
  assert.equal(by["FG%"].awayLabel, "44%");
  assert.deepEqual([by["3P%"].away, by["3P%"].home], [27, 36]);
  assert.equal(by.REB.awayLabel, "41");
  near(by.REB.awayWidth, 95.35);
  assert.equal(by.REB.homeWidth, 100);
  assert.equal(by.AST.awayWidth, 100);
  near(by.AST.homeWidth, 82.76);
  near(by.STL.homeWidth, 66.67);
  assert.equal(by.TO.awayWidth, 75);
  assert.equal(by.TO.homeWidth, 100);
  assert.deepEqual([by.PF.awayWidth, by.PF.homeWidth], [100, 100]);
});

function synthetic(away: Record<string, string>, home: Record<string, string>) {
  const g = parseSummary(fixture("espn-summary-final.json"));
  return {
    ...g,
    boxes: g.boxes.map((b) => ({ ...b, teamStats: b.espnId === g.away.espnId ? away : home })),
  };
}

test("teamComparison handles zero and missing stats without NaN", () => {
  const rows = teamComparison(synthetic({ assists: "0", steals: "3" }, { assists: "0" }));
  const by = Object.fromEntries(rows.map((r) => [r.key, r]));
  assert.deepEqual([by.AST.awayWidth, by.AST.homeWidth, by.AST.awayLabel], [0, 0, "0"]);
  assert.deepEqual(
    [by.STL.away, by.STL.home, by.STL.homeLabel, by.STL.awayWidth, by.STL.homeWidth],
    [3, null, "–", 100, 0],
  );
  assert.deepEqual([by["FG%"].away, by["FG%"].awayLabel, by["FG%"].awayWidth], [null, "–", 0]);
  for (const r of rows) assert.ok(!Number.isNaN(r.awayWidth) && !Number.isNaN(r.homeWidth));
});

test("teamComparison without boxes yields empty cells", () => {
  const g = { ...parseSummary(fixture("espn-summary-final.json")), boxes: [] };
  const rows = teamComparison(g);
  assert.equal(rows.length, 7);
  assert.ok(rows.every((r) => r.away === null && r.homeWidth === 0));
});
