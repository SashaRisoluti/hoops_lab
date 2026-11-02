"use client";

import tokens from "@/tokens.json";
import { boxRows, boxTotals } from "@/lib/live/boxscore";
import { matchupAccents } from "@/lib/live/colors";
import { teamComparison } from "@/lib/live/comparison";
import { teamFoulsThisPeriod, timeoutsUsed } from "@/lib/live/counts";
import { clockLabel, lastPlayText, tipOffLabel } from "@/lib/live/format";
import { onCourt } from "@/lib/live/lineup";
import { possession } from "@/lib/live/possession";
import { lastShots } from "@/lib/live/shots";
import type { GameSummary, ScoreboardGame, Side } from "@/lib/live/types";
import { BoxScore } from "./BoxScore";
import { GameChips } from "./GameChips";
import { LiveCourt } from "./LiveCourt";
import { LiveScorebar } from "./LiveScorebar";
import { TeamComparison } from "./TeamComparison";
import { useLiveGame } from "./useLiveGame";

const Note = ({ children }: { children: string }) => (
  <p className="card p-4 text-sm text-ink-soft">{children}</p>
);

function Detail({ summary, accents }: { summary: GameSummary; accents: Record<Side, string> }) {
  // On-court markers only while the game is in progress.
  const court = summary.state === "in" ? onCourt(summary) : { home: [], away: [] };
  const teams = (["away", "home"] as const).flatMap((side) => {
    const team = summary[side];
    const box = summary.boxes.find((b) => b.espnId === team.espnId);
    return box
      ? [
          {
            tricode: team.tricode,
            accent: accents[side],
            rows: boxRows(box, court[side]),
            totals: boxTotals(box, team.score),
          },
        ]
      : [];
  });
  return (
    <>
      <LiveCourt
        shots={lastShots(summary)}
        possession={summary.state === "in" ? possession(summary) : null}
        awayTricode={summary.away.tricode}
        homeTricode={summary.home.tricode}
        awayAccent={accents.away}
        homeAccent={accents.home}
        lastPlay={lastPlayText(summary)}
      />
      <TeamComparison
        rows={teamComparison(summary)}
        awayTricode={summary.away.tricode}
        homeTricode={summary.home.tricode}
        awayAccent={accents.away}
        homeAccent={accents.home}
      />
      {teams.length ? <BoxScore teams={teams} /> : <Note>Box score not available.</Note>}
    </>
  );
}

/** The /live page body: game chips, scorebar and, once ESPN has data, court, comparison, box score. */
export function LiveGame() {
  const { status, games, selectedId, select, summary, updatedAt, stale, failedId } = useLiveGame();

  if (status === "loading") return <Note>Loading games…</Note>;
  if (status === "error") return <Note>Couldn&apos;t reach ESPN — try again later.</Note>;
  if (status === "empty") return <Note>No NBA games to show right now.</Note>;

  const game: ScoreboardGame | undefined = games.find((g) => g.id === selectedId);
  const sum = summary && summary.id === selectedId ? summary : null;
  const home = sum?.home ?? game?.home;
  const away = sum?.away ?? game?.away;
  if (!home || !away) return null;

  const accents = matchupAccents(
    home.tricode,
    away.tricode,
    tokens.teamAccents,
    tokens.teamPairOverrides,
    tokens.tokens.primary,
  );
  const polled = (sum ?? game)?.state === "in";
  const scheduled = (sum?.state ?? game?.state) === "pre";

  return (
    <div className="space-y-4">
      <GameChips games={games} selectedId={selectedId} onSelect={select} />
      <LiveScorebar
        away={{ tricode: away.tricode, score: scheduled ? null : away.score }}
        home={{ tricode: home.tricode, score: scheduled ? null : home.score }}
        awayAccent={accents.away}
        homeAccent={accents.home}
        clock={sum ? clockLabel(sum) : (game?.statusDetail ?? "")}
        fouls={sum ? teamFoulsThisPeriod(sum) : null}
        timeouts={sum ? timeoutsUsed(sum) : null}
        updatedAt={updatedAt}
        stale={stale && polled}
        tipOff={scheduled && game ? tipOffLabel(game.startTime) : null}
        live={sum?.state === "in"}
      />
      {scheduled ? <Note>This game has not started yet.</Note> : null}
      {!sum && !scheduled && failedId === selectedId ? (
        <Note>Game details not available — select the game again to retry.</Note>
      ) : null}
      {sum && !scheduled ? <Detail summary={sum} accents={accents} /> : null}
    </div>
  );
}
