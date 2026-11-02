import { test } from "node:test";
import assert from "node:assert/strict";
import { matchupAccents } from "../../lib/live/colors.ts";

const accents = { CHI: "#ce1141", HOU: "#ce1141", BOS: "#007a33" };
const overrides = { "CHI-HOU": { CHI: "#000000" } };

test("clashing pair uses the override, whichever side", () => {
  assert.deepEqual(matchupAccents("HOU", "CHI", accents, overrides, "#0000ff"), { home: "#ce1141", away: "#000000" });
  assert.deepEqual(matchupAccents("CHI", "HOU", accents, overrides, "#0000ff"), { home: "#000000", away: "#ce1141" });
});

test("non-clashing pair is plain", () => {
  assert.deepEqual(matchupAccents("BOS", "CHI", accents, overrides, "#0000ff"), { home: "#007a33", away: "#ce1141" });
});

test("unknown tricode falls back", () => {
  assert.deepEqual(matchupAccents("XXX", "BOS", accents, overrides, "#0000ff"), { home: "#0000ff", away: "#007a33" });
});
