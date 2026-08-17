"""Command-line interface for the Selenium extraction workflow."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from football_results_scraper.browser import managed_chrome_driver
from football_results_scraper.exporters import write_matches
from football_results_scraper.models import build_summary
from football_results_scraper.pages.results_page import ResultsPage

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Use Selenium WebDriver to extract deduplicated football results from a dynamic page."
        )
    )
    parser.add_argument(
        "--country",
        default="England",
        help="Country name shown in the website filter",
    )
    parser.add_argument(
        "--league",
        default="Premier League",
        help="League name shown in the website filter",
    )
    parser.add_argument("--season", help="Optional season label, for example 2025/2026")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/football_results.csv"),
        help="Destination ending in .csv or .json",
    )
    parser.add_argument("--headed", action="store_true", help="Show Chrome while the run executes")
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="Optional path for a successful browser screenshot",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="Explicit wait timeout in seconds",
    )
    parser.add_argument(
        "--url",
        default=ResultsPage.DEFAULT_URL,
        help="Results page URL, mainly useful for controlled test environments",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with managed_chrome_driver(headless=not args.headed) as driver:
        page = ResultsPage(driver, timeout=args.timeout)
        try:
            page.open(args.url)
            if page.dismiss_optional_consent():
                LOGGER.info("Dismissed the consent banner")

            page.select_competition(
                country=args.country,
                league=args.league,
                season=args.season,
            )
            page.show_all_matches()
            matches = page.extract_matches(
                country=args.country,
                league=args.league,
                season=args.season,
            )

            output_path = write_matches(matches, args.output)
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                driver.save_screenshot(str(args.screenshot))

            LOGGER.info("Saved %d unique matches to %s", len(matches), output_path)
            print(json.dumps(build_summary(matches).to_record(), indent=2))
            return 0
        except Exception:
            screenshot, page_source = page.save_diagnostics(Path("artifacts"))
            LOGGER.exception(
                "Automation failed. Diagnostics saved to %s and %s",
                screenshot,
                page_source,
            )
            return 1
