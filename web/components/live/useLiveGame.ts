"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchScoreboard, fetchSummary } from "@/lib/live/espnClient";
import { needsPreviousDay, pickGame, previousDayParam, shouldPoll } from "@/lib/live/selection";
import type { GameSummary, ScoreboardGame } from "@/lib/live/types";

const POLL_MS = 30_000;
const byStart = (a: ScoreboardGame, b: ScoreboardGame) => a.startTime.localeCompare(b.startTime);

export type LiveGameState = {
  status: "loading" | "ready" | "empty" | "error";
  games: ScoreboardGame[];
  selectedId: string | null;
  select: (id: string) => void;
  summary: GameSummary | null;
  updatedAt: number | null;
  stale: boolean;
};

/** Loads the scoreboard and the selected game from ESPN; polls only if a game was live at load. */
export function useLiveGame(): LiveGameState {
  const [status, setStatus] = useState<LiveGameState["status"]>("loading");
  const [games, setGames] = useState<ScoreboardGame[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<GameSummary | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [stale, setStale] = useState(false);

  const selected = useRef<string | null>(null);
  const gamesRef = useRef<ScoreboardGame[]>([]);
  const previous = useRef<ScoreboardGame[]>([]);
  const summaryState = useRef<string | null>(null);
  const request = useRef(0); // ignores summary responses superseded by a newer request

  const loadSummary = useCallback(async (id: string) => {
    const mine = ++request.current;
    try {
      const s = await fetchSummary(id);
      if (mine !== request.current || selected.current !== id) return;
      summaryState.current = s.state;
      setSummary(s);
      setUpdatedAt(Date.now());
      setStale(false);
    } catch {
      if (mine === request.current) setStale(true);
    }
  }, []);

  const select = useCallback(
    (id: string) => {
      selected.current = id;
      setSelectedId(id);
      setSummary(null);
      summaryState.current = null;
      history.replaceState(null, "", `?game=${id}`);
      if (gamesRef.current.find((g) => g.id === id)?.state !== "pre") void loadSummary(id);
    },
    [loadSummary],
  );

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setInterval> | undefined;
    let ticking = false;

    const setAll = (today: ScoreboardGame[]) => {
      const all = [...previous.current, ...today].sort(byStart);
      gamesRef.current = all;
      setGames(all);
    };

    const onVisible = () => {
      if (!document.hidden) void tick();
    };
    const stop = () => {
      if (timer) clearInterval(timer);
      timer = undefined;
      document.removeEventListener("visibilitychange", onVisible);
    };

    async function tick() {
      if (ticking || document.hidden) return;
      ticking = true;
      try {
        const board = await fetchScoreboard();
        if (!alive) return;
        setAll(board.games);
        const id = selected.current;
        const g = board.games.find((x) => x.id === id);
        // One more summary after the game ends captures the final box score.
        if (id && g && (g.state === "in" || (g.state === "post" && summaryState.current === "in")))
          await loadSummary(id);
        else setStale(false);
        if (!shouldPoll(board.games)) stop();
      } catch {
        if (alive) setStale(true);
      } finally {
        ticking = false;
      }
    }

    (async () => {
      try {
        const today = await fetchScoreboard();
        let prev: ScoreboardGame[] = [];
        if (needsPreviousDay(today.games) && today.day)
          prev = (await fetchScoreboard(previousDayParam(today.day))).games;
        if (!alive) return;
        previous.current = prev;
        setAll(today.games);
        const requested = new URLSearchParams(window.location.search).get("game");
        const id = pickGame(today.games, prev, requested);
        selected.current = id;
        setSelectedId(id);
        if (id === null) return setStatus("empty");
        setStatus("ready");
        const g = gamesRef.current.find((x) => x.id === id);
        if (g && g.state !== "pre") await loadSummary(id);
        if (alive && shouldPoll(today.games)) {
          timer = setInterval(() => void tick(), POLL_MS);
          document.addEventListener("visibilitychange", onVisible);
        }
      } catch {
        if (alive) setStatus("error");
      }
    })();

    return () => {
      alive = false;
      stop();
    };
  }, [loadSummary]);

  return { status, games, selectedId, select, summary, updatedAt, stale };
}
