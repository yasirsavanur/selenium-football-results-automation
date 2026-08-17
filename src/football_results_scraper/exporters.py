"""CSV and JSON output adapters."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from football_results_scraper.models import MatchResult

CSV_FIELDS = (
    "date",
    "country",
    "league",
    "season",
    "home_team",
    "away_team",
    "score",
    "home_goals",
    "away_goals",
    "total_goals",
    "outcome",
    "source_url",
)


def write_matches(matches: list[MatchResult], output_path: Path) -> Path:
    """Write matches based on the requested file extension and return the path."""

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.casefold()
    if suffix == ".csv":
        _write_csv(matches, output_path)
    elif suffix == ".json":
        _write_json(matches, output_path)
    else:
        raise ValueError("Output must use a .csv or .json extension")

    return output_path


def _write_csv(matches: list[MatchResult], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(match.to_record() for match in matches)


def _write_json(matches: list[MatchResult], output_path: Path) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "match_count": len(matches),
        "matches": [match.to_record() for match in matches],
    }
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
