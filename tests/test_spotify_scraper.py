"""tests/test_spotify_scraper.py — Unit tests for SpotifyScraper (mocked WebDriver)."""

from unittest.mock import MagicMock, patch

import pytest

from src.config import AppConfig
from src.exceptions import SpotifyPlaylistNotFoundError, SpotifyScrapingError
from src.spotify_scraper import SpotifyScraper


def _make_driver(body_text="3 songs", rows=3, js_result=None):
    driver = MagicMock()
    # body text used to detect expected track count
    body = MagicMock()
    body.text = body_text
    driver.find_element.return_value = body
    # tracklist rows
    row_list = [MagicMock() for _ in range(rows)]
    driver.find_elements.return_value = row_list
    # JS extraction result (and scrollIntoView returns are ignored)
    driver.execute_script.return_value = js_result or {"name": "Song", "artist": "Artist"}
    return driver


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("src.spotify_scraper.time.sleep", return_value=None):
        yield


class TestGetExpectedCount:
    def test_parses_song_count(self):
        driver = _make_driver(body_text="This playlist has 25 songs total")
        scraper = SpotifyScraper(driver, AppConfig())
        assert scraper._get_expected_track_count() == 25

    def test_returns_none_when_no_count(self):
        driver = _make_driver(body_text="no numbers about songs here")
        scraper = SpotifyScraper(driver, AppConfig())
        assert scraper._get_expected_track_count() is None


class TestGetTracks:
    def test_happy_path_via_js(self):
        driver = _make_driver(body_text="3 songs", rows=3)
        scraper = SpotifyScraper(driver, AppConfig())
        tracks = scraper.get_tracks("https://open.spotify.com/playlist/abc")

        assert len(tracks) == 3
        assert tracks[0].name == "Song"
        assert tracks[0].artist == "Artist"

    def test_raises_when_no_tracks_extracted(self):
        # No detectable count and zero rows → nothing extracted → error raised
        driver = _make_driver(body_text="nothing parseable here", rows=0)
        scraper = SpotifyScraper(driver, AppConfig())
        with pytest.raises(SpotifyScrapingError):
            scraper.get_tracks("https://open.spotify.com/playlist/abc")


class TestWaitForTracklist:
    def test_raises_playlist_not_found_on_timeout(self):
        from selenium.common.exceptions import TimeoutException

        driver = MagicMock()
        scraper = SpotifyScraper(driver, AppConfig())
        scraper.wait = MagicMock()
        scraper.wait.until.side_effect = TimeoutException("timeout")
        with pytest.raises(SpotifyPlaylistNotFoundError):
            scraper._wait_for_tracklist()
