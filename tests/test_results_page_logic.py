from pathlib import Path

import pytest
from selenium.webdriver.common.by import By

from football_results_scraper.pages.results_page import ResultsNotFoundError, ResultsPage


class FakeCell:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeRow:
    def __init__(self, values: list[str], *, displayed: bool = True) -> None:
        self.cells = [FakeCell(value) for value in values]
        self.displayed = displayed

    def is_displayed(self) -> bool:
        return self.displayed

    def find_elements(self, by: str, value: str):
        assert (by, value) == (By.TAG_NAME, "td")
        return self.cells


class FakePageDriver:
    current_url = "https://example.test/results"
    page_source = "<html><h1>Failure evidence</h1></html>"

    def __init__(self, rows: list[FakeRow]) -> None:
        self.rows = rows

    def find_elements(self, by: str, value: str):
        return self.rows

    def save_screenshot(self, path: str) -> bool:
        Path(path).write_bytes(b"fake-png")
        return True


def test_extract_matches_skips_invalid_rows_and_removes_duplicates() -> None:
    valid = ["16-08-2026", "", "Arsenal", "2 - 1", "Chelsea", ""]
    rows = [
        FakeRow(valid),
        FakeRow(valid),
        FakeRow(["16-08-2026", "too few"]),
        FakeRow(["15-08-2026", "", "Liverpool", "postponed", "Everton", ""]),
        FakeRow(valid, displayed=False),
    ]
    page = ResultsPage(FakePageDriver(rows), timeout=1)

    matches = page.extract_matches(
        country="England",
        league="Premier League",
        season="2025/2026",
    )

    assert len(matches) == 1
    assert matches[0].total_goals == 3


def test_extract_matches_raises_when_every_row_is_invalid() -> None:
    page = ResultsPage(FakePageDriver([FakeRow(["bad"])]), timeout=1)

    with pytest.raises(ResultsNotFoundError, match="No completed matches"):
        page.extract_matches(
            country="England",
            league="Premier League",
            season="2025/2026",
        )


def test_save_diagnostics_writes_both_files(tmp_path: Path) -> None:
    page = ResultsPage(FakePageDriver([]), timeout=1)

    screenshot, html = page.save_diagnostics(tmp_path / "nested")

    assert screenshot.read_bytes() == b"fake-png"
    assert "Failure evidence" in html.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("16-08-2026", (2026, 8, 16)),
        ("2026-08-16", (2026, 8, 16)),
        ("unknown", (0, 0, 0)),
    ],
)
def test_date_sort_key_handles_supported_and_unknown_dates(date: str, expected) -> None:
    match = type("Match", (), {"date": date})()

    assert ResultsPage._date_sort_key(match) == expected
