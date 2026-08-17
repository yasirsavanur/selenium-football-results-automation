"""Domain models and small analytical summaries for scraped match results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_SCORE_PATTERN = re.compile(r"(?P<home>\d+)\s*[-–—:]\s*(?P<away>\d+)")
_DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _parse_date(value: str) -> datetime | None:
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue
    return None


@dataclass(frozen=True, slots=True)
class MatchResult:
    """One completed football match plus its competition context."""

    date: str
    home_team: str
    score: str
    away_team: str
    country: str
    league: str
    season: str
    source_url: str

    def __post_init__(self) -> None:
        for field_name in ("date", "home_team", "score", "away_team", "country", "league"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty")
        if not _SCORE_PATTERN.fullmatch(_clean(self.score)):
            raise ValueError(f"Unsupported score format: {self.score!r}")

    @property
    def home_goals(self) -> int:
        return self._score_groups[0]

    @property
    def away_goals(self) -> int:
        return self._score_groups[1]

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return "Home win"
        if self.home_goals < self.away_goals:
            return "Away win"
        return "Draw"

    @property
    def duplicate_key(self) -> tuple[str, ...]:
        """Return a case-insensitive key used to remove repeated team-panel rows."""

        return tuple(
            _clean(value).casefold()
            for value in (
                self.country,
                self.league,
                self.season,
                self.date,
                self.home_team,
                self.away_team,
                f"{self.home_goals}-{self.away_goals}",
            )
        )

    @property
    def _score_groups(self) -> tuple[int, int]:
        match = _SCORE_PATTERN.fullmatch(_clean(self.score))
        if match is None:  # Protected by __post_init__; retained for type narrowing.
            raise ValueError(f"Unsupported score format: {self.score!r}")
        return int(match.group("home")), int(match.group("away"))

    def to_record(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "country": self.country,
            "league": self.league,
            "season": self.season,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "score": _clean(self.score),
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "total_goals": self.total_goals,
            "outcome": self.outcome,
            "source_url": self.source_url,
        }


@dataclass(frozen=True, slots=True)
class ScrapeSummary:
    """Compact quality check and descriptive summary for an extraction run."""

    match_count: int
    total_goals: int
    average_goals: float
    home_wins: int
    draws: int
    away_wins: int
    earliest_match: str | None
    latest_match: str | None

    def to_record(self) -> dict[str, Any]:
        return {
            "match_count": self.match_count,
            "total_goals": self.total_goals,
            "average_goals": self.average_goals,
            "home_wins": self.home_wins,
            "draws": self.draws,
            "away_wins": self.away_wins,
            "earliest_match": self.earliest_match,
            "latest_match": self.latest_match,
        }


def build_summary(matches: list[MatchResult]) -> ScrapeSummary:
    """Calculate basic result checks without introducing a dataframe dependency."""

    parsed_dates = [parsed for match in matches if (parsed := _parse_date(match.date))]
    match_count = len(matches)
    total_goals = sum(match.total_goals for match in matches)

    return ScrapeSummary(
        match_count=match_count,
        total_goals=total_goals,
        average_goals=round(total_goals / match_count, 2) if match_count else 0.0,
        home_wins=sum(match.outcome == "Home win" for match in matches),
        draws=sum(match.outcome == "Draw" for match in matches),
        away_wins=sum(match.outcome == "Away win" for match in matches),
        earliest_match=min(parsed_dates).date().isoformat() if parsed_dates else None,
        latest_match=max(parsed_dates).date().isoformat() if parsed_dates else None,
    )
