import { test } from "node:test";
import assert from "node:assert/strict";
import { parseScoreboard, parseSummary, toNbaTricode } from "../../lib/live/espn.ts";
import { fixture } from "../load.ts";

test("toNbaTricode maps ESPN abbreviations", () => {
  const cases: [string, string][] = [
    ["GS", "GSW"],
    ["NO", "NOP"],
    ["NY", "NYK"],
    ["SA", "SAS"],
    ["UTAH", "UTA"],
    ["WSH", "WAS"],
    ["BOS", "BOS"],
  ];
  for (const [espn, nba] of cases) assert.equal(toNbaTricode(espn), nba);
});

test("parseSummary final game", () => {
  const g = parseSummary(fixture("espn-summary-final.json"));
  assert.equal(g.id, "401909903");
  assert.equal(g.state, "post");
  assert.equal(g.period, 4);
  assert.equal(g.statusDetail, "Final");
  assert.deepEqual(
    { id: g.home.espnId, t: g.home.tricode, s: g.home.score, side: g.home.side, p: g.home.hasPossession },
    { id: "19", t: "ORL", s: 97, side: "home", p: false },
  );
  assert.deepEqual(
    { id: g.away.espnId, t: g.away.tricode, s: g.away.score, side: g.away.side, p: g.away.hasPossession },
    { id: "2", t: "BOS", s: 108, side: "away", p: false },
  );
  assert.equal(g.plays.length, 485);
  assert.equal(g.boxes.length, 2);

  const bos = g.boxes.find((b) => b.espnId === "2")!;
  const george = bos.players.find((p) => p.athleteId === "4251")!;
  assert.equal(george.starter, true);
  assert.deepEqual(george.stats, {
    MIN: "33", PTS: "17", FG: "6-14", "3PT": "3-10", FT: "2-2", REB: "6", AST: "8",
    TO: "4", STL: "2", BLK: "2", OREB: "2", DREB: "4", PF: "2", "+/-": "+10",
  });
  const conley = bos.players.find((p) => p.athleteId === "3195")!;
  assert.equal(conley.didNotPlay, true);
  assert.equal(conley.reason, "COACH'S DECISION");
  assert.deepEqual(conley.stats, {});
  assert.equal(bos.teamStats.fouls, "22");
  assert.equal(bos.teamStats.fieldGoalPct, "44");

  const sub = g.plays.find((p) => p.seq === 72)!;
  assert.equal(sub.type, "Substitution");
  assert.equal(sub.teamId, "19");
  assert.deepEqual(sub.participants, ["4278572", "4066320"]);
  assert.equal(sub.coordinate, null);

  const three = g.plays.find((p) => p.text.startsWith("Wendell Carter Jr. makes 22-foot three"))!;
  assert.deepEqual(three.coordinate, { x: 2, y: 1 });
  assert.equal(three.scoringPlay, true);
  assert.equal(three.scoreValue, 3);
  assert.equal(three.teamId, "19");
});

test("parseSummary live game", () => {
  const g = parseSummary(fixture("espn-summary-live.json"));
  assert.equal(g.state, "in");
  assert.equal(g.period, 3);
  assert.equal(g.clock, "4:58");
  assert.equal(g.home.score, 59);
  assert.equal(g.away.score, 69);
  assert.equal(g.away.hasPossession, true);
  assert.equal(g.plays.length, 303);
});

test("parseSummary pre game", () => {
  const g = parseSummary(fixture("espn-summary-pre.json"));
  assert.equal(g.state, "pre");
  assert.deepEqual(g.plays, []);
  assert.deepEqual(g.boxes, []);
  assert.equal(g.home.score, 0);
});

test("parseSummary tolerates an empty payload", () => {
  const g = parseSummary({});
  assert.equal(g.state, "pre");
  assert.deepEqual(g.plays, []);
  assert.deepEqual(g.boxes, []);
  assert.equal(g.id, "");
  assert.equal(g.home.tricode, "");
  assert.equal(g.away.espnId, "");
});

test("parseScoreboard today", () => {
  const s = parseScoreboard(fixture("espn-scoreboard-today.json"));
  assert.equal(s.day, "2026-11-02");
  assert.equal(s.games.length, 15);
  const g0 = s.games[0];
  assert.equal(g0.id, "401909907");
  assert.equal(g0.state, "pre");
  assert.equal(g0.startTime, "2026-11-03T00:00Z");
  assert.deepEqual(g0.away, { tricode: "OKC", score: null });
  assert.deepEqual(g0.home, { tricode: "CLE", score: null });
  assert.equal(s.games.find((g) => g.away.tricode === "UTA")!.home.tricode, "SAS");
});

test("parseScoreboard past day", () => {
  const s = parseScoreboard(fixture("espn-scoreboard-2026-11-01.json"));
  assert.equal(s.day, null);
  assert.equal(s.games.length, 4);
  assert.ok(s.games.every((g) => g.state === "post"));
  const g = s.games.find((x) => x.id === "401909903")!;
  assert.deepEqual(g.away, { tricode: "BOS", score: 108 });
  assert.deepEqual(g.home, { tricode: "ORL", score: 97 });
});

type Raw = Record<string, any>;
const raw = (name: string) => structuredClone(fixture(name)) as Raw;

test("parseSummary play ids and running scores", () => {
  const g = parseSummary(fixture("espn-summary-final.json"));
  assert.equal(g.plays.find((p) => p.seq === 72)!.id, "40190990372");
  const last = g.plays[g.plays.length - 1];
  assert.equal(typeof last.homeScore, "number");
  assert.equal(parseSummary({ plays: [{}] }).plays[0].homeScore, 0);
  assert.equal(parseSummary({ plays: [{ homeScore: 5, awayScore: 7 }] }).plays[0].awayScore, 7);
});

test("parseSummary win probability, season type, neutral site", () => {
  const r = raw("espn-summary-final.json");
  r.winprobability = [{ homeWinPercentage: 0.376, tiePercentage: 0, playId: "4019099034" }];
  r.header.season = { year: 2026, type: 3 };
  r.header.competitions[0].neutralSite = true;
  const g = parseSummary(r);
  assert.deepEqual(g.espnWinProbability, [{ playId: "4019099034", home: 0.376 }]);
  assert.equal(g.seasonType, 3);
  assert.equal(g.neutralSite, true);

  const d = parseSummary(fixture("espn-summary-final.json"));
  assert.deepEqual(d.espnWinProbability, []);
  assert.equal(d.seasonType, 2);
  assert.equal(d.neutralSite, false);
});

test("parseSummary drops win probability entries without a finite percentage", () => {
  const r = raw("espn-summary-final.json");
  r.winprobability = [
    { homeWinPercentage: 0.4, playId: "a" },
    { homeWinPercentage: null, playId: "b" },
    { playId: "c" },
    { homeWinPercentage: "n/a", playId: "d" },
    { homeWinPercentage: Number.NaN, playId: "e" },
    { homeWinPercentage: 0, playId: "f" },
  ];
  assert.deepEqual(parseSummary(r).espnWinProbability, [
    { playId: "a", home: 0.4 },
    { playId: "f", home: 0 },
  ]);
});

test("parseScoreboard season type and neutral site", () => {
  const r = raw("espn-scoreboard-today.json");
  r.events[0].season = { type: 1 };
  r.events[0].competitions[0].neutralSite = true;
  const s = parseScoreboard(r);
  assert.equal(s.games[0].seasonType, 1);
  assert.equal(s.games[0].neutralSite, true);
  assert.equal(s.games[1].seasonType, 2);
  assert.equal(s.games[1].neutralSite, false);
});
