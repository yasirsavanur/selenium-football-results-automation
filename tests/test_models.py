import pytest

from football_results_scraper.models import MatchResult, build_summary


def make_match(**overrides: str) -> MatchResult:
    values = {
        "date": "16-08-2026",
        "home_team": "Arsenal",
        "score": "2 - 1",
        "away_team": "Chelsea",
        "country": "England",
        "league": "Premier League",
        "season": "2025/2026",
        "source_url": "https://example.test/results",
    }
    values.update(overrides)
    return MatchResult(**values)


def test_match_result_parses_score_and_outcome() -> None:
    match = make_match()

    assert match.home_goals == 2
    assert match.away_goals == 1
    assert match.total_goals == 3
    assert match.outcome == "Home win"


@pytest.mark.parametrize("score", ["2 to 1", "postponed", ""])
def test_match_result_rejects_invalid_scores(score: str) -> None:
    with pytest.raises(ValueError, match="score"):
        make_match(score=score)


def test_duplicate_key_ignores_case_and_extra_spacing() -> None:
    first = make_match()
    second = make_match(home_team="  ARSENAL ", score="2-1")

    assert first.duplicate_key == second.duplicate_key


def test_build_summary_returns_result_counts_and_date_range() -> None:
    matches = [
        make_match(),
        make_match(date="15-08-2026", home_team="Liverpool", away_team="Everton", score="1-1"),
        make_match(date="14-08-2026", home_team="Leeds", away_team="Villa", score="0-2"),
    ]

    summary = build_summary(matches)

    assert summary.match_count == 3
    assert summary.total_goals == 7
    assert summary.average_goals == 2.33
    assert (summary.home_wins, summary.draws, summary.away_wins) == (1, 1, 1)
    assert summary.earliest_match == "2026-08-14"
    assert summary.latest_match == "2026-08-16"
