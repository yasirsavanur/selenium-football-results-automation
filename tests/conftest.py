from __future__ import annotations

import os
from pathlib import Path

import pytest
from selenium.common.exceptions import WebDriverException

from football_results_scraper.browser import create_chrome_driver


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def driver(request: pytest.FixtureRequest):
    try:
        browser = create_chrome_driver(headless=True)
    except WebDriverException as error:
        if os.getenv("CI"):
            raise
        pytest.skip(f"Chrome is unavailable locally: {error.msg}")

    yield browser

    report = getattr(request.node, "rep_call", None)
    if report and report.failed:
        artifact_dir = Path("artifacts")
        artifact_dir.mkdir(exist_ok=True)
        browser.save_screenshot(str(artifact_dir / f"{request.node.name}.png"))
        (artifact_dir / f"{request.node.name}.html").write_text(
            browser.page_source,
            encoding="utf-8",
        )

    browser.quit()


@pytest.fixture
def results_fixture_url() -> str:
    fixture = Path(__file__).parent / "fixtures" / "results_page.html"
    return fixture.resolve().as_uri()
