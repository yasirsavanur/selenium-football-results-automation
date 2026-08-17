from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from football_results_scraper import cli
from football_results_scraper.models import MatchResult


class FakeDriver:
    def __init__(self) -> None:
        self.screenshots: list[Path] = []

    def save_screenshot(self, path: str) -> bool:
        screenshot = Path(path)
        screenshot.write_bytes(b"fake-png")
        self.screenshots.append(screenshot)
        return True


class FakeResultsPage:
    def __init__(self, *, fail_on_open: bool = False) -> None:
        self.fail_on_open = fail_on_open
        self.calls: list[object] = []

    def open(self, url: str):
        self.calls.append(("open", url))
        if self.fail_on_open:
            raise RuntimeError("controlled failure")
        return self

    def dismiss_optional_consent(self) -> bool:
        self.calls.append("consent")
        return True

    def select_competition(self, **filters):
        self.calls.append(("filters", filters))
        return self

    def show_all_matches(self):
        self.calls.append("all_matches")
        return self

    def extract_matches(self, **filters) -> list[MatchResult]:
        self.calls.append(("extract", filters))
        return [
            MatchResult(
                date="16-08-2026",
                home_team="Arsenal",
                score="2-1",
                away_team="Chelsea",
                country=filters["country"],
                league=filters["league"],
                season=filters["season"] or "2025/2026",
                source_url="https://example.test/results",
            )
        ]

    def save_diagnostics(self, directory: Path) -> tuple[Path, Path]:
        self.calls.append("diagnostics")
        return directory / "failure.png", directory / "failure.html"


def install_fake_browser(monkeypatch, page: FakeResultsPage) -> FakeDriver:
    driver = FakeDriver()

    @contextmanager
    def fake_managed_driver(*, headless: bool):
        assert isinstance(headless, bool)
        yield driver

    default_url = cli.ResultsPage.DEFAULT_URL

    class PageFactory:
        DEFAULT_URL = default_url

        def __new__(cls, driver, timeout):
            return page

    monkeypatch.setattr(cli, "managed_chrome_driver", fake_managed_driver)
    monkeypatch.setattr(cli, "ResultsPage", PageFactory)
    return driver


def test_main_runs_complete_workflow(monkeypatch, tmp_path: Path, capsys) -> None:
    page = FakeResultsPage()
    driver = install_fake_browser(monkeypatch, page)
    output = tmp_path / "results.json"
    screenshot = tmp_path / "success.png"

    exit_code = cli.main(
        [
            "--country",
            "England",
            "--league",
            "Premier League",
            "--season",
            "2025/2026",
            "--output",
            str(output),
            "--screenshot",
            str(screenshot),
            "--url",
            "https://example.test/results",
        ]
    )

    assert exit_code == 0
    assert output.exists()
    assert driver.screenshots == [screenshot]
    assert "all_matches" in page.calls
    assert '"match_count": 1' in capsys.readouterr().out


def test_main_saves_diagnostics_after_failure(monkeypatch) -> None:
    page = FakeResultsPage(fail_on_open=True)
    install_fake_browser(monkeypatch, page)

    exit_code = cli.main(["--url", "https://example.test/broken"])

    assert exit_code == 1
    assert "diagnostics" in page.calls


def test_parser_exposes_portable_defaults() -> None:
    args = cli.build_parser().parse_args([])

    assert args.country == "England"
    assert args.league == "Premier League"
    assert args.output == Path("data/football_results.csv")
    assert args.headed is False
