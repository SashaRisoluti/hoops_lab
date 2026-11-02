"use client";

import { useState, type KeyboardEvent } from "react";
import { BOX_COLUMNS } from "@/lib/live/boxscore";
import type { BoxColumn, BoxRow } from "@/lib/live/types";

type Team = { tricode: string; accent: string; rows: BoxRow[]; totals: Record<BoxColumn, string> };

/**
 * Box score with one tab per team (away first). On-court players are marked, bench is
 * muted, DNP rows show the reason, foul trouble highlights PF, and a totals row closes
 * the table. The table scrolls horizontally on narrow screens.
 */
export function BoxScore({ teams }: { teams: Team[] }) {
  const [sel, setSel] = useState(0);
  const team = teams[sel] ?? teams[0];
  if (!team) return null;

  const onKey = (e: KeyboardEvent) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (d) setSel((sel + d + teams.length) % teams.length);
  };

  return (
    <div className="rounded-lg border border-line bg-card">
      <div role="tablist" aria-label="Team box score" className="flex border-b border-line" onKeyDown={onKey}>
        {teams.map((t, i) => (
          <button
            key={t.tricode}
            type="button"
            role="tab"
            id={`box-tab-${t.tricode}`}
            aria-selected={i === sel}
            aria-controls={`box-panel-${t.tricode}`}
            tabIndex={i === sel ? 0 : -1}
            onClick={() => setSel(i)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold ${
              i === sel ? "text-ink" : "text-ink-muted"
            }`}
          >
            <span
              className="inline-block h-3 w-3 rounded-sm ring-1 ring-ink-soft"
              style={{ backgroundColor: t.accent }}
            />
            {t.tricode}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`box-panel-${team.tricode}`}
        aria-labelledby={`box-tab-${team.tricode}`}
        className="overflow-x-auto"
      >
        <table className="w-full min-w-max text-sm tabular-nums">
          <thead>
            <tr className="border-b border-line text-xs text-ink-muted">
              <th scope="col" className="px-3 py-2 text-left font-medium">
                Player
              </th>
              {BOX_COLUMNS.map((c) => (
                <th key={c} scope="col" className="px-2 py-2 text-right font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {team.rows.map((r) => (
              <tr
                key={r.athleteId}
                className={`border-b border-line ${r.onCourt ? "text-ink" : "text-ink-muted"}`}
              >
                <th scope="row" className="whitespace-nowrap px-3 py-1.5 text-left font-normal">
                  {r.onCourt && (
                    <>
                      <span aria-hidden="true">● </span>
                      <span className="sr-only">on court </span>
                    </>
                  )}
                  {r.name}
                </th>
                {r.didNotPlay ? (
                  <td colSpan={BOX_COLUMNS.length} className="px-2 py-1.5 text-left italic">
                    {r.reason ?? "Did not play"}
                  </td>
                ) : (
                  BOX_COLUMNS.map((c) => (
                    <td
                      key={c}
                      className={`px-2 py-1.5 text-right ${
                        c === "PF" && r.foulTrouble ? "font-bold text-weak" : ""
                      }`}
                    >
                      {r.cells[c]}
                    </td>
                  ))
                )}
              </tr>
            ))}
            <tr className="font-bold text-ink">
              <th scope="row" className="px-3 py-2 text-left">
                Total
              </th>
              {BOX_COLUMNS.map((c) => (
                <td key={c} className="px-2 py-2 text-right">
                  {team.totals[c]}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
