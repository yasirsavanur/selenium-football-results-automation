"""WebDriver creation and lifecycle management."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver


def create_chrome_driver(*, headless: bool = True) -> WebDriver:
    """Create a Chrome session using Selenium Manager for driver discovery.

    No local ChromeDriver path is required. Selenium uses an installed compatible
    driver when available and otherwise delegates driver management to Selenium
    Manager.
    """

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-GB")

    if headless:
        options.add_argument("--headless=new")

    is_root = getattr(os, "geteuid", lambda: 1)() == 0
    if os.getenv("CI") or is_root:
        options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


@contextmanager
def managed_chrome_driver(*, headless: bool = True) -> Iterator[WebDriver]:
    """Yield a Chrome driver and guarantee that the session is closed."""

    driver = create_chrome_driver(headless=headless)
    try:
        yield driver
    finally:
        driver.quit()
