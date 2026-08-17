"""Page object for the dynamic football statistics results page."""

from __future__ import annotations

import logging
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from football_results_scraper.models import MatchResult

LOGGER = logging.getLogger(__name__)


class CompetitionNotFoundError(ValueError):
    """Raised when the requested country, league, or season is unavailable."""


class ResultsNotFoundError(RuntimeError):
    """Raised when no completed match rows can be extracted."""


class ResultsPage:
    """Encapsulate navigation, filtering, waiting, and result extraction."""

    DEFAULT_URL = "https://www.adamchoi.co.uk/overs/detailed"

    COUNTRY_SELECT = (By.ID, "country")
    LEAGUE_SELECT = (By.ID, "league")
    SEASON_SELECT = (By.ID, "season")
    ALL_MATCHES = (By.CSS_SELECTOR, "label[analytics-event='All matches']")
    LOADING_INDICATOR = (By.CSS_SELECTOR, "loading-indicator")
    RESULT_ROWS = (
        By.XPATH,
        "//detailed-team//tr[starts-with(normalize-space(@data-ng-repeat), 'match in')]",
    )

    CONSENT_BUTTONS = (
        (
            By.XPATH,
            "//button[normalize-space()='Consent' or .//p[normalize-space()='Consent']]",
        ),
        (
            By.XPATH,
            "//button[normalize-space()='Accept all' or normalize-space()='Accept All']",
        ),
        (
            By.XPATH,
            "//*[@role='button'][normalize-space()='Consent' or normalize-space()='Accept all']",
        ),
    )

    def __init__(self, driver: WebDriver, *, timeout: float = 20) -> None:
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout, poll_frequency=0.25)

    def open(self, url: str | None = None) -> ResultsPage:
        self.driver.get(url or self.DEFAULT_URL)
        self.wait.until(expected.presence_of_element_located(self.COUNTRY_SELECT))
        return self

    def dismiss_optional_consent(self) -> bool:
        """Dismiss a consent control in the document or a consent-related iframe.

        The banner is regional and is not always present, so absence is not an error.
        """

        if self._click_first_consent_button():
            return True

        frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            metadata = " ".join(
                (frame.get_attribute("title") or "", frame.get_attribute("src") or "")
            ).casefold()
            if not any(keyword in metadata for keyword in ("consent", "privacy", "message")):
                continue

            try:
                self.driver.switch_to.frame(frame)
                if self._click_first_consent_button():
                    return True
            except NoSuchElementException:
                continue
            finally:
                self.driver.switch_to.default_content()

        return False

    def select_competition(
        self,
        *,
        country: str,
        league: str,
        season: str | None = None,
    ) -> ResultsPage:
        self._select_visible_text(self.COUNTRY_SELECT, country, "country")
        self._select_visible_text(self.LEAGUE_SELECT, league, "league")

        if season is not None:
            self._select_visible_text(self.SEASON_SELECT, season, "season")

        self._wait_until_not_loading()
        return self

    def show_all_matches(self) -> ResultsPage:
        button = self.wait.until(expected.element_to_be_clickable(self.ALL_MATCHES))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)

        try:
            button.click()
        except ElementClickInterceptedException:
            LOGGER.info("Normal click was intercepted; using a JavaScript click fallback")
            self.driver.execute_script("arguments[0].click();", button)

        self._wait_for_results_to_stabilise()
        return self

    def extract_matches(
        self,
        *,
        country: str,
        league: str,
        season: str | None = None,
    ) -> list[MatchResult]:
        rows = [row for row in self.driver.find_elements(*self.RESULT_ROWS) if row.is_displayed()]
        matches: list[MatchResult] = []
        seen: set[tuple[str, ...]] = set()

        selected_season = season or self._selected_text(self.SEASON_SELECT)

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5:
                LOGGER.warning("Skipping a result row with only %d cells", len(cells))
                continue

            try:
                match = MatchResult(
                    date=self._text(cells[0]),
                    home_team=self._text(cells[2]),
                    score=self._text(cells[3]),
                    away_team=self._text(cells[4]),
                    country=country,
                    league=league,
                    season=selected_season,
                    source_url=self.driver.current_url,
                )
            except ValueError as error:
                LOGGER.warning("Skipping an unrecognised result row: %s", error)
                continue

            if match.duplicate_key not in seen:
                seen.add(match.duplicate_key)
                matches.append(match)

        if not matches:
            raise ResultsNotFoundError(
                "No completed matches were found. The page layout or selected "
                "competition may have changed."
            )

        return sorted(matches, key=self._date_sort_key, reverse=True)

    def save_diagnostics(self, directory: Path) -> tuple[Path, Path]:
        """Save a screenshot and DOM snapshot after an automation failure."""

        directory.mkdir(parents=True, exist_ok=True)
        screenshot_path = directory / "failure.png"
        page_source_path = directory / "failure.html"
        self.driver.save_screenshot(str(screenshot_path))
        page_source_path.write_text(self.driver.page_source, encoding="utf-8")
        return screenshot_path, page_source_path

    def _select_visible_text(self, locator: tuple[str, str], text: str, label: str) -> None:
        def option_is_available(driver: WebDriver) -> bool:
            select = Select(driver.find_element(*locator))
            return any(option.text.strip() == text for option in select.options)

        try:
            self.wait.until(option_is_available)
        except TimeoutException as error:
            options = self._available_options(locator)
            raise CompetitionNotFoundError(
                f"{label.title()} {text!r} was not available. Options: {options}"
            ) from error

        select = Select(self.driver.find_element(*locator))
        select.select_by_visible_text(text)
        self.wait.until(lambda driver: self._selected_text(locator) == text)

    def _available_options(self, locator: tuple[str, str]) -> list[str]:
        try:
            return [
                option.text.strip()
                for option in Select(self.driver.find_element(*locator)).options
                if option.text.strip()
            ]
        except NoSuchElementException:
            return []

    def _selected_text(self, locator: tuple[str, str]) -> str:
        try:
            return Select(self.driver.find_element(*locator)).first_selected_option.text.strip()
        except NoSuchElementException:
            return ""

    def _wait_until_not_loading(self) -> None:
        self.wait.until(
            lambda driver: not any(
                element.is_displayed()
                for element in driver.find_elements(*self.LOADING_INDICATOR)
            )
        )

    def _wait_for_results_to_stabilise(self) -> None:
        state: dict[str, object] = {"signature": None, "matches": 0}

        def rows_are_stable(driver: WebDriver) -> bool:
            if any(
                element.is_displayed()
                for element in driver.find_elements(*self.LOADING_INDICATOR)
            ):
                state.update(signature=None, matches=0)
                return False

            rows = [row for row in driver.find_elements(*self.RESULT_ROWS) if row.is_displayed()]
            signature = tuple(row.get_attribute("textContent").strip() for row in rows)
            if not signature:
                state.update(signature=None, matches=0)
                return False

            if signature == state["signature"]:
                state["matches"] = int(state["matches"]) + 1
            else:
                state.update(signature=signature, matches=0)

            return int(state["matches"]) >= 2

        self.wait.until(rows_are_stable)

    def _click_first_consent_button(self) -> bool:
        for locator in self.CONSENT_BUTTONS:
            for button in self.driver.find_elements(*locator):
                if not button.is_displayed() or not button.is_enabled():
                    continue
                try:
                    button.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", button)
                return True
        return False

    @staticmethod
    def _text(element: object) -> str:
        text = getattr(element, "text", "")
        return " ".join(str(text).split())

    @staticmethod
    def _date_sort_key(match: MatchResult) -> tuple[int, int, int]:
        try:
            first, second, third = (
                int(part) for part in match.date.replace("/", "-").split("-")
            )
        except (TypeError, ValueError):
            return (0, 0, 0)
        if first > 31:  # ISO date format.
            return (first, second, third)
        return (third, second, first)
