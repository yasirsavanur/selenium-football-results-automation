from pathlib import Path

import pytest

from football_results_scraper.pages.results_page import CompetitionNotFoundError, ResultsPage


@pytest.mark.browser
def test_page_object_selects_filters_extracts_and_deduplicates(
    driver,
    results_fixture_url: str,
) -> None:
    page = ResultsPage(driver, timeout=5)

    matches = (
        page.open(results_fixture_url)
        .select_competition(country="England", league="Premier League", season="2025/2026")
        .show_all_matches()
        .extract_matches(country="England", league="Premier League", season="2025/2026")
    )

    assert len(matches) == 2
    assert matches[0].home_team == "Arsenal"
    assert matches[0].source_url.startswith("file:")
    assert {match.away_team for match in matches} == {"Chelsea", "Everton"}


@pytest.mark.browser
def test_page_object_reports_available_options(driver, results_fixture_url: str) -> None:
    page = ResultsPage(driver, timeout=0.5).open(results_fixture_url)

    with pytest.raises(CompetitionNotFoundError, match="Spanish League") as error:
        page.select_competition(country="Spain", league="Spanish League")

    assert "Premier League" in str(error.value)


@pytest.mark.browser
def test_failure_diagnostics_are_written(driver, results_fixture_url: str, tmp_path: Path) -> None:
    page = ResultsPage(driver, timeout=1).open(results_fixture_url)

    screenshot, html = page.save_diagnostics(tmp_path)

    assert screenshot.stat().st_size > 0
    assert "Football results test fixture" in html.read_text(encoding="utf-8")
