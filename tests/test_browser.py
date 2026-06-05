from unittest.mock import MagicMock, patch

from selenium.common.exceptions import WebDriverException

from src.utils import browser
from src.utils.browser import create_driver, find_element_with_fallback, managed_browser


def _element(displayed: bool):
    el = MagicMock()
    el.is_displayed.return_value = displayed
    return el


class TestFindElementWithFallback:
    def test_returns_first_visible_element(self):
        driver = MagicMock()
        visible = _element(True)
        driver.find_elements.return_value = [_element(False), visible]

        result = find_element_with_fallback(driver, [("css", ".x", "first")])
        assert result is visible

    def test_tries_next_strategy_when_first_empty(self):
        driver = MagicMock()
        wanted = _element(True)
        driver.find_elements.side_effect = [[], [wanted]]

        result = find_element_with_fallback(
            driver, [("css", ".a", "a"), ("css", ".b", "b")]
        )
        assert result is wanted

    def test_returns_none_when_nothing_found(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        result = find_element_with_fallback(driver, [("css", ".x", "x")])
        assert result is None

    def test_skips_strategy_that_raises(self):
        driver = MagicMock()
        wanted = _element(True)
        driver.find_elements.side_effect = [WebDriverException("bad"), [wanted]]

        result = find_element_with_fallback(
            driver, [("css", ".a", "a"), ("css", ".b", "b")]
        )
        assert result is wanted


class TestCreateDriver:
    @patch("src.utils.browser.webdriver.Chrome")
    def test_headless_adds_argument(self, mock_chrome):
        create_driver(headless=True, window_size="800,600")
        options = mock_chrome.call_args.kwargs["options"]
        args = options.arguments
        assert any("--headless" in a for a in args)
        assert any("800,600" in a for a in args)

    @patch("src.utils.browser.webdriver.Chrome")
    def test_non_headless_omits_headless(self, mock_chrome):
        create_driver(headless=False)
        options = mock_chrome.call_args.kwargs["options"]
        assert not any("--headless" in a for a in options.arguments)


class TestManagedBrowser:
    def test_quits_on_normal_exit(self):
        mock_driver = MagicMock()
        with patch.object(browser, "create_driver", return_value=mock_driver):
            with managed_browser() as (driver, wait):
                assert driver is mock_driver
        mock_driver.quit.assert_called_once()

    def test_quits_on_exception(self):
        mock_driver = MagicMock()
        with patch.object(browser, "create_driver", return_value=mock_driver):
            try:
                with managed_browser():
                    raise ValueError("boom")
            except ValueError:
                pass
        mock_driver.quit.assert_called_once()

    def test_keep_open_on_error_pauses_then_quits(self):
        mock_driver = MagicMock()
        with patch.object(browser, "create_driver", return_value=mock_driver), \
             patch("builtins.input", return_value="") as mock_input:
            try:
                with managed_browser(keep_open_on_error=True):
                    raise ValueError("boom")
            except ValueError:
                pass
        mock_input.assert_called_once()        # paused for inspection
        mock_driver.quit.assert_called_once()  # still closed afterwards

    def test_no_pause_when_headless(self):
        mock_driver = MagicMock()
        with patch.object(browser, "create_driver", return_value=mock_driver), \
             patch("builtins.input") as mock_input:
            try:
                with managed_browser(headless=True, keep_open_on_error=True):
                    raise ValueError("boom")
            except ValueError:
                pass
        mock_input.assert_not_called()         # no point pausing a headless run
        mock_driver.quit.assert_called_once()
