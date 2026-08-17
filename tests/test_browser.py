from football_results_scraper import browser


class FakeWebDriver:
    def __init__(self) -> None:
        self.page_load_timeout = None
        self.quit_called = False

    def set_page_load_timeout(self, timeout: int) -> None:
        self.page_load_timeout = timeout

    def quit(self) -> None:
        self.quit_called = True


def test_create_chrome_driver_configures_portable_headless_session(monkeypatch) -> None:
    fake_driver = FakeWebDriver()
    captured = {}

    def fake_chrome(*, options):
        captured["options"] = options
        return fake_driver

    monkeypatch.setattr(browser.webdriver, "Chrome", fake_chrome)

    result = browser.create_chrome_driver(headless=True)

    assert result is fake_driver
    assert fake_driver.page_load_timeout == 45
    assert "--headless=new" in captured["options"].arguments
    assert "--window-size=1440,1200" in captured["options"].arguments


def test_managed_driver_always_quits(monkeypatch) -> None:
    fake_driver = FakeWebDriver()
    monkeypatch.setattr(browser, "create_chrome_driver", lambda **kwargs: fake_driver)

    with browser.managed_chrome_driver(headless=False) as active_driver:
        assert active_driver is fake_driver

    assert fake_driver.quit_called is True
