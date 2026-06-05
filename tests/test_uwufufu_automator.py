"""tests/test_uwufufu_automator.py — Unit tests for UwuFufuAutomator (mocked WebDriver)."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException

from src.config import AppConfig
from src.exceptions import LoginError
from src.models import Credentials, Track, YoutubeLink
from src.uwufufu_automator import UwuFufuAutomator


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("src.uwufufu_automator.time.sleep", return_value=None):
        yield


def _displayed(value=True):
    el = MagicMock()
    el.is_displayed.return_value = value
    return el


def _automator(driver):
    auto = UwuFufuAutomator(driver, AppConfig())
    # Replace the real WebDriverWait with a mock that returns a clickable element
    auto.wait = MagicMock()
    auto.wait.until.return_value = _displayed(True)
    return auto


class TestLogin:
    def test_login_success(self):
        driver = MagicMock()
        driver.current_url = "https://uwufufu.com/dashboard"
        auto = _automator(driver)

        auto.login(Credentials(email="a@b.com", password="pw"))

        driver.get.assert_called()  # navigated to login page

    def test_login_failure_raises(self):
        driver = MagicMock()
        auto = _automator(driver)
        auto.wait.until.side_effect = TimeoutException("no redirect")

        with pytest.raises(LoginError):
            auto.login(Credentials(email="a@b.com", password="pw"))


class TestLoginRedirectCheck:
    """Regression tests for the post-login URL check (uses the real WebDriverWait)."""

    @staticmethod
    def _driver_with_clickable_fields(current_url):
        """A mock driver whose elements satisfy EC.element_to_be_clickable.

        EC compares ``is_displayed() == True``, so the element must return real
        booleans (a bare MagicMock would never be considered clickable).
        """
        driver = MagicMock()
        driver.current_url = current_url
        el = MagicMock()
        el.is_displayed.return_value = True
        el.is_enabled.return_value = True
        driver.find_element.return_value = el
        return driver

    def test_www_subdomain_counts_as_success(self):
        # The old check `url_contains("https://uwufufu.com")` failed when the app
        # redirected to a www. subdomain after login. Leaving /auth/login = success.
        driver = self._driver_with_clickable_fields("https://www.uwufufu.com/dashboard")
        auto = UwuFufuAutomator(driver, AppConfig())  # real WebDriverWait

        auto.login(Credentials(email="a@b.com", password="pw"))  # must not raise
        driver.get.assert_called()

    def test_stuck_on_login_page_raises(self):
        driver = self._driver_with_clickable_fields("https://uwufufu.com/auth/login")
        auto = UwuFufuAutomator(driver, AppConfig(webdriver_timeout=1))

        with pytest.raises(LoginError):
            auto.login(Credentials(email="a@b.com", password="pw"))


class TestNavigate:
    def test_navigate_via_selector(self):
        driver = MagicMock()
        driver.current_url = "https://uwufufu.com/create-game"
        driver.find_elements.return_value = [_displayed(True)]
        auto = _automator(driver)

        auto.navigate_to_create_game()  # should not raise

    def test_navigate_direct_fallback(self):
        driver = MagicMock()
        # No elements found and JS returns falsy → falls through to direct navigation
        driver.find_elements.return_value = []
        driver.execute_script.return_value = False
        driver.current_url = "https://uwufufu.com/create-game"
        auto = _automator(driver)

        auto.navigate_to_create_game()
        # Direct navigation calls driver.get with the create-game URL
        assert any("create-game" in str(c) for c in driver.get.call_args_list)


class TestAddVideo:
    def test_add_video_success(self):
        driver = MagicMock()
        driver.find_elements.return_value = [_displayed(True)]
        auto = _automator(driver)

        link = YoutubeLink(Track("Song", "Artist"), url="https://youtu.be/x")
        assert auto.add_video(link) is True

    def test_add_video_no_input_returns_false(self):
        driver = MagicMock()
        auto = _automator(driver)
        # _find_youtube_input falls back to JS which returns None here
        auto.wait.until.side_effect = TimeoutException("no input")
        driver.find_elements.return_value = []
        driver.execute_script.return_value = None

        link = YoutubeLink(Track("Song", "Artist"), url="https://youtu.be/x")
        assert auto.add_video(link) is False


class TestAddAllVideos:
    def test_invokes_callback_and_marks_added(self):
        driver = MagicMock()
        driver.find_elements.return_value = [_displayed(True)]
        auto = _automator(driver)

        links = [
            YoutubeLink(Track("A", "1"), url="https://youtu.be/a"),
            YoutubeLink(Track("B", "2"), url="https://youtu.be/b"),
        ]
        marked = []
        success, total = auto.add_all_videos(links, on_added=marked.append)

        assert (success, total) == (2, 2)
        assert len(marked) == 2
        assert all(link.added for link in links)
