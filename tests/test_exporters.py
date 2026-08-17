import csv
import json
from pathlib import Path

import pytest

from football_results_scraper.exporters import write_matches
from football_results_scraper.models import MatchResult


@pytest.fixture
def match() -> MatchResult:
    return MatchResult(
        date="16-08-2026",
        home_team="Arsenal",
        score="2 - 1",
        away_team="Chelsea",
        country="England",
        league="Premier League",
        season="2025/2026",
        source_url="https://example.test/results",
    )


def test_write_matches_to_csv(tmp_path: Path, match: MatchResult) -> None:
    output = write_matches([match], tmp_path / "nested" / "matches.csv")

    with output.open(encoding="utf-8", newline="") as output_file:
        rows = list(csv.DictReader(output_file))

    assert rows[0]["home_team"] == "Arsenal"
    assert rows[0]["total_goals"] == "3"


def test_write_matches_to_json(tmp_path: Path, match: MatchResult) -> None:
    output = write_matches([match], tmp_path / "matches.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["match_count"] == 1
    assert payload["matches"][0]["outcome"] == "Home win"


def test_write_matches_rejects_unknown_extension(tmp_path: Path, match: MatchResult) -> None:
    with pytest.raises(ValueError, match=".csv or .json"):
        write_matches([match], tmp_path / "matches.txt")
