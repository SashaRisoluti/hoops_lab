import type { GameSummary, Side } from "./types";

/**
 * Players on the floor now: each side's starters, then substitutions applied in play order
 * (`participants[0]` enters, `participants[1]` leaves). Malformed substitutions are skipped.
 */
export function onCourt(summary: GameSummary): Record<Side, string[]> {
  const sets: Record<Side, Set<string>> = { home: new Set(), away: new Set() };
  const sideOf = (teamId: string | null): Side | null =>
    teamId === summary.home.espnId ? "home" : teamId === summary.away.espnId ? "away" : null;

  for (const box of summary.boxes) {
    const side = sideOf(box.espnId);
    if (!side) continue;
    for (const p of box.players) if (p.starter && !p.didNotPlay) sets[side].add(p.athleteId);
  }

  for (const p of summary.plays) {
    if (p.type !== "Substitution" || p.participants.length < 2) continue;
    const side = sideOf(p.teamId);
    if (!side) continue;
    const [entering, leaving] = p.participants;
    if (!sets[side].delete(leaving)) continue;
    sets[side].add(entering);
  }

  return { home: [...sets.home], away: [...sets.away] };
}
