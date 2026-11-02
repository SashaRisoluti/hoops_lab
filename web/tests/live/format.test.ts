import { test } from "node:test";
import assert from "node:assert/strict";
import { parseSummary } from "../../lib/live/espn.ts";
import { clockLabel, lastPlayText, periodLabel, tipOffLabel } from "../../lib/live/format.ts";
import { fixture } from "../load.ts";

const final = parseSummary(fixture("espn-summary-final.json"));
const live = parseSummary(fixture("espn-summary-live.json"));
const pre = parseSummary(fixture("espn-summary-pre.json"));

test("periodLabel", () => {
  assert.deepEqual([1, 4, 5, 6, 7].map(periodLabel), ["Q1", "Q4", "OT", "2OT", "3OT"]);
});

test("clockLabel", () => {
  assert.equal(clockLabel(live), "Q3 · 4:58");
  assert.equal(clockLabel(final), "Final");
  assert.equal(clockLabel(pre), "Scheduled");
});

test("clockLabel: between periods shows ESPN's status text, not a 0.0 clock", () => {
  assert.equal(clockLabel({ ...live, period: 2, clock: "0.0", statusDetail: "Halftime" }), "Halftime");
  assert.equal(
    clockLabel({ ...live, clock: "", statusDetail: "End of 3rd Quarter" }),
    "End of 3rd Quarter",
  );
});

test("tipOffLabel", () => {
  assert.equal(tipOffLabel("2026-11-03T00:00Z", "Europe/Rome"), "01:00");
  assert.equal(tipOffLabel("2026-11-03T00:00Z", "America/New_York"), "19:00");
});

test("tipOffLabel: a missing or malformed date renders a dash instead of throwing", () => {
  assert.equal(tipOffLabel(""), "–");
  assert.equal(tipOffLabel("not a date"), "–");
});

test("lastPlayText", () => {
  assert.equal(lastPlayText(final), "End of Game");
  assert.equal(lastPlayText(live), "Jayson Tatum misses 25-foot three point jumper");
  assert.equal(lastPlayText(pre), null);
});
