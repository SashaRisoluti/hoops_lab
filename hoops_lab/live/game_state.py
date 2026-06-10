"""Current game state: a reducer over PBPv3-format events.

``GameState.from_events`` consumes the events seen so far (live or replay)
and produces live KPIs; possessions are re-segmented with the same parser
used for historical data, so live PPP/pace are consistent with the
historical baselines by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from hoops_lab.features.possession import _clock_seconds, build_possessions


@dataclass
class TeamLiveStats:
    """Box-score counts accumulated from the event stream."""

    fgm: int = 0
    fga: int = 0
    fg3m: int = 0
    fg3a: int = 0
    ftm: int = 0
    fta: int = 0
    tov: int = 0

    @property
    def efg_pct(self) -> float | None:
        """Effective FG% (None until the first attempt)."""
        if self.fga == 0:
            return None
        return (self.fgm + 0.5 * self.fg3m) / self.fga


def _column_or_na(events: pd.DataFrame, name: str) -> pd.Series:
    """A column if present, else an all-NA series aligned to the index."""
    if name in events.columns:
        return events[name]
    return pd.Series(pd.NA, index=events.index)


def shot_frame_from_events(events: pd.DataFrame) -> pd.DataFrame:
    """Shot-chart-shaped frame (LOC_X/LOC_Y/...) from PBP-format events.

    Rows without legacy coordinates are dropped; ``ASSISTED`` is derived from
    the play-by-play description ("... (Irving 4 AST)") on made shots.
    """
    shots = events.loc[events["actionType"].isin(["Made Shot", "Missed Shot"])]
    made = shots["actionType"] == "Made Shot"
    frame = pd.DataFrame(
        {
            "LOC_X": pd.to_numeric(_column_or_na(shots, "xLegacy"), errors="coerce"),
            "LOC_Y": pd.to_numeric(_column_or_na(shots, "yLegacy"), errors="coerce"),
            "SHOT_MADE_FLAG": made.astype(int),
            "PLAYER_NAME": _column_or_na(shots, "playerName").astype(str),
            "SHOT_DISTANCE": pd.to_numeric(_column_or_na(shots, "shotDistance"), errors="coerce"),
            "ACTION_TYPE": _column_or_na(shots, "subType").astype(str),
            "ASSISTED": made
            & _column_or_na(shots, "description").astype(str).str.contains(" AST)", regex=False),
            "TEAM_ID": _column_or_na(shots, "teamId"),
        }
    )
    return frame.dropna(subset=["LOC_X", "LOC_Y"]).reset_index(drop=True)


@dataclass
class GameState:
    """Snapshot of a game after N events."""

    home_id: int
    away_id: int
    period: int
    clock: str
    score: tuple[int, int]
    team_stats: dict[int, TeamLiveStats]
    possessions: pd.DataFrame
    events_seen: int = 0
    last_events: pd.DataFrame = field(default_factory=pd.DataFrame)

    @classmethod
    def from_events(cls, events: pd.DataFrame, home_id: int, away_id: int) -> GameState:
        """Reduce the events seen so far into a state snapshot."""
        shots = events.loc[events["actionType"].isin(["Made Shot", "Missed Shot"])]
        free_throws = events.loc[events["actionType"] == "Free Throw"]
        turnovers = events.loc[events["actionType"] == "Turnover"]

        team_stats: dict[int, TeamLiveStats] = {}
        for team_id in (home_id, away_id):
            team_shots = shots.loc[shots["teamId"] == team_id]
            made = team_shots["actionType"] == "Made Shot"
            threes = pd.to_numeric(team_shots["shotValue"], errors="coerce") == 3
            team_fts = free_throws.loc[free_throws["teamId"] == team_id]
            ft_made = ~team_fts["description"].astype(str).str.contains("MISS")
            team_stats[team_id] = TeamLiveStats(
                fgm=int(made.sum()),
                fga=int(len(team_shots)),
                fg3m=int((made & threes).sum()),
                fg3a=int(threes.sum()),
                ftm=int(ft_made.sum()),
                fta=int(len(team_fts)),
                tov=int((turnovers["teamId"] == team_id).sum()),
            )

        home_score = pd.to_numeric(events["scoreHome"], errors="coerce").ffill().fillna(0)
        away_score = pd.to_numeric(events["scoreAway"], errors="coerce").ffill().fillna(0)
        last = events.iloc[-1] if len(events) else None

        return cls(
            home_id=home_id,
            away_id=away_id,
            period=int(last["period"]) if last is not None else 1,
            clock=str(last["clock"]) if last is not None else "PT12M00.00S",
            score=(int(home_score.iloc[-1]), int(away_score.iloc[-1])) if len(events) else (0, 0),
            team_stats=team_stats,
            possessions=build_possessions(events),
            events_seen=len(events),
            last_events=events.tail(12),
        )

    # ---- Possession-derived metrics -----------------------------------------

    def possession_count(self, team_id: int) -> int:
        """Completed possessions for one team."""
        if self.possessions.empty:
            return 0
        return int((self.possessions["offense_team_id"] == team_id).sum())

    def ppp(self, team_id: int) -> float | None:
        """Points per possession (None until the first completed trip)."""
        count = self.possession_count(team_id)
        if count == 0:
            return None
        team = self.possessions.loc[self.possessions["offense_team_id"] == team_id]
        return float(team["points"].sum()) / count

    @property
    def minutes_elapsed(self) -> float:
        """Game minutes played so far (regulation 12' quarters + 5' OTs)."""
        clock_sec = _clock_seconds(pd.Series([self.clock])).iloc[0]
        if pd.isna(clock_sec):
            clock_sec = 0.0
        period_length = 12.0 if self.period <= 4 else 5.0
        completed = min(self.period - 1, 4) * 12.0 + max(self.period - 5, 0) * 5.0
        return completed + (period_length - clock_sec / 60.0)

    @property
    def pace_estimate(self) -> float | None:
        """Possessions per team per 48 minutes (None in the first minute)."""
        if self.minutes_elapsed < 1.0 or self.possessions.empty:
            return None
        per_team = len(self.possessions) / 2.0
        return per_team / self.minutes_elapsed * 48.0

    def last_run(self, n: int = 8) -> tuple[int, int]:
        """(home points, away points) over the last ``n`` completed possessions."""
        tail = self.possessions.tail(n)
        home = int(tail.loc[tail["offense_team_id"] == self.home_id, "points"].sum())
        away = int(tail.loc[tail["offense_team_id"] == self.away_id, "points"].sum())
        return home, away

    def recent_turnovers(self, team_id: int, last_n_team_possessions: int = 6) -> int:
        """Turnover-ended trips among the team's last N possessions."""
        team = self.possessions.loc[self.possessions["offense_team_id"] == team_id]
        tail = team.tail(last_n_team_possessions)
        return int((tail["ended_by"] == "turnover").sum())
