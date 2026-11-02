import type { GameState, ScoreboardGame } from "./types";

/**
 * What one poll tick does. The selected game's summary is reloaded while either the board
 * or its last loaded summary says it is in progress, so the final box score is always
 * fetched even when ESPN's scoreboard flips to final first. Polling stops only when no
 * board game is in progress AND the selected summary is no longer in progress.
 * Known limit: if ESPN never flips the summary to final, polling continues while visible.
 */
export function pollDecision(input: {
  games: ScoreboardGame[];
  selectedId: string | null;
  summaryState: GameState | null;
}): { loadSummary: boolean; stop: boolean } {
  const { games, selectedId, summaryState } = input;
  const summaryLive = summaryState === "in";
  const boardLive = games.some((g) => g.state === "in"); // same check as selection.shouldPoll
  const selectedLive = games.some((g) => g.id === selectedId && g.state === "in");
  return {
    loadSummary: selectedId !== null && (selectedLive || summaryLive),
    stop: !boardLive && !summaryLive,
  };
}
