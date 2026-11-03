import { test } from "node:test";
import assert from "node:assert/strict";
import { pollDecision } from "../../lib/live/polling.ts";
import type { GameState, ScoreboardGame } from "../../lib/live/types.ts";

const game = (id: string, state: GameState): ScoreboardGame => ({
  id,
  state,
  startTime: "2026-11-03T00:00Z",
  statusDetail: "",
  neutralSite: false,
  seasonType: 2,
  home: { tricode: "BOS", score: null },
  away: { tricode: "ORL", score: null },
});

const cases: [string, Parameters<typeof pollDecision>[0], ReturnType<typeof pollDecision>][] = [
  [
    "selected game in progress on the board",
    { games: [game("1", "in")], selectedId: "1", summaryState: "in" },
    { loadSummary: true, stop: false },
  ],
  [
    "board says final but the summary is still in progress",
    { games: [game("1", "post")], selectedId: "1", summaryState: "in" },
    { loadSummary: true, stop: false },
  ],
  [
    "board and summary both final",
    { games: [game("1", "post")], selectedId: "1", summaryState: "post" },
    { loadSummary: false, stop: true },
  ],
  [
    "no selected game and nothing in progress",
    { games: [game("1", "post"), game("2", "pre")], selectedId: null, summaryState: null },
    { loadSummary: false, stop: true },
  ],
  [
    "selected game dropped from the board (day rollover), summary in progress",
    { games: [game("2", "pre")], selectedId: "1", summaryState: "in" },
    { loadSummary: true, stop: false },
  ],
  [
    "another game still in progress, selected one final",
    { games: [game("1", "post"), game("2", "in")], selectedId: "1", summaryState: "post" },
    { loadSummary: false, stop: false },
  ],
];

for (const [name, input, want] of cases) {
  test(`pollDecision: ${name}`, () => {
    assert.deepEqual(pollDecision(input), want);
  });
}
