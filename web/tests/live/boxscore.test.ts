import { test } from "node:test";
import assert from "node:assert/strict";
import { BOX_COLUMNS, boxRows, boxTotals } from "../../lib/live/boxscore.ts";
import { parseSummary } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";

const summary = parseSummary(fixture("espn-summary-final.json"));
const bos = summary.boxes.find((b) => b.espnId === summary.away.espnId)!;
const ON_COURT = ["4397424", "3078576", "5175647", "4593841", "4683689"];

test("BOX_COLUMNS order", () => {
  assert.deepEqual([...BOX_COLUMNS], ["MIN", "PTS", "REB", "AST", "STL", "BLK", "TO", "PF", "FG", "3PT", "FT", "+/-"]);
});

test("boxRows orders on court, bench, then DNP", () => {
  const rows = boxRows(bos, ON_COURT);
  assert.deepEqual(
    rows.map((r) => r.athleteId),
    ["4397424", "3078576", "5175647", "4593841", "4683689", "4251", "4065648", "4065804", "4277951", "4066354",
      "4702745", "5142621", "3195", "4397251"],
  );
  assert.ok(rows.slice(0, 5).every((r) => r.onCourt));
  assert.ok(rows.slice(5).every((r) => !r.onCourt));
  assert.equal(rows[0].name, "Neemias Queta");
  const dnp = rows[12];
  assert.equal(dnp.didNotPlay, true);
  assert.equal(dnp.reason, "COACH'S DECISION");
  assert.ok(BOX_COLUMNS.every((c) => dnp.cells[c] === ""));
  assert.equal(rows[5].cells.PTS, "17");
  assert.equal(rows[5].cells["3PT"], "3-10");
});

test("foulTrouble at 5 or 6 fouls, not 4, without mutating input", () => {
  const withPf = (pf: string) => ({
    ...bos,
    players: bos.players.map((p) => (p.athleteId === "4251" ? { ...p, stats: { ...p.stats, PF: pf } } : p)),
  });
  const trouble = (pf: string) => boxRows(withPf(pf), []).find((r) => r.athleteId === "4251")!.foulTrouble;
  assert.equal(trouble("4"), false);
  assert.equal(trouble("5"), true);
  assert.equal(trouble("6"), true);
  assert.equal(bos.players.find((p) => p.athleteId === "4251")!.stats.PF, "2");
});

test("boxTotals", () => {
  assert.deepEqual(boxTotals(bos, 108), {
    MIN: "", PTS: "108", REB: "41", AST: "29", STL: "9", BLK: "7", TO: "12", PF: "22",
    FG: "37-84", "3PT": "12-44", FT: "22-26", "+/-": "",
  });
  assert.equal(boxTotals({ ...bos, teamStats: {} }, 0).FG, "");
});
