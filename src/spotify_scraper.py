"""
spotify_scraper.py — Spotify playlist scraper for Uwufufu-Automator

Extracts tracks from a public Spotify playlist using Selenium (no API key required).
"""

from __future__ import annotations

import logging
import re
import time
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import AppConfig
from src.exceptions import SpotifyPlaylistNotFoundError, SpotifyScrapingError
from src.models import Track

logger = logging.getLogger(__name__)

_TRACK_COUNT_PATTERNS = [
    r"(\d+)\s+songs?",
    r"(\d+)\s+tracks?",
    r"(\d+)\s+songs?,\s+\d+\s+hr",
    r"(\d+)\s+songs?,\s+\d+\s+min",
]


class SpotifyScraper:
    """Scrapes track data from a public Spotify playlist page."""

    def __init__(self, driver: WebDriver, config: AppConfig) -> None:
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.webdriver_timeout)
        self._selectors = config.selectors
        self._timing = config.timing

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_tracks(self, playlist_url: str) -> List[Track]:
        """Return all tracks from the given Spotify playlist URL.

        Raises:
            SpotifyPlaylistNotFoundError: If the tracklist never loads.
            SpotifyScrapingError: If no tracks could be extracted.
        """
        logger.info("Accessing Spotify playlist...")
        self.driver.get(playlist_url)

        self._wait_for_tracklist()
        time.sleep(self._timing.spotify_initial_load)

        expected = self._get_expected_track_count()
        row_elements = self._scroll_to_load_all(expected)

        tracks = self._extract_tracks_js(row_elements)

        if len(tracks) < min(10, len(row_elements)):
            logger.warning("JS extraction yielded too few results — trying Selenium fallback")
            tracks = self._extract_tracks_selenium(row_elements)

        if not tracks:
            raise SpotifyScrapingError(
                "Failed to extract any tracks from the playlist. "
                "Spotify may have updated its HTML structure."
            )

        logger.info("Extracted %d tracks from playlist", len(tracks))
        return tracks

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _wait_for_tracklist(self) -> None:
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, self._selectors.tracklist_row)
                )
            )
        except Exception as exc:
            raise SpotifyPlaylistNotFoundError(
                "Tracklist did not load. Check that the URL is correct "
                "and the playlist is set to Public."
            ) from exc

    def _get_expected_track_count(self) -> Optional[int]:
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        for pattern in _TRACK_COUNT_PATTERNS:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                logger.info("Playlist reports %d tracks", count)
                return count
        logger.debug("Could not determine expected track count from page text")
        return None

    def _scroll_to_load_all(self, expected: Optional[int]):
        """Scroll down until all tracks are loaded; return the row elements."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, self._selectors.tracklist_row)
        logger.info("Scrolling to load all tracks...")

        if expected:
            while len(rows) < expected:
                self.driver.execute_script("arguments[0].scrollIntoView();", rows[-1])
                time.sleep(self._timing.between_scroll)
                rows = self.driver.find_elements(By.CSS_SELECTOR, self._selectors.tracklist_row)
                if len(rows) >= expected or len(rows) > expected * 1.5:
                    break
        else:
            last_count = 0
            while len(rows) > last_count:
                last_count = len(rows)
                self.driver.execute_script("arguments[0].scrollIntoView();", rows[-1])
                time.sleep(self._timing.between_scroll)
                rows = self.driver.find_elements(By.CSS_SELECTOR, self._selectors.tracklist_row)

        if expected and len(rows) > expected:
            rows = rows[:expected]

        logger.info("Found %d track rows in playlist", len(rows))
        return rows

    def _extract_tracks_js(self, row_elements) -> List[Track]:
        """Extract track data via JavaScript execution (faster, less flaky)."""
        tracks: List[Track] = []
        for i, element in enumerate(row_elements):
            try:
                data = self.driver.execute_script("""
                    const row = arguments[0];
                    const nameEl = row.querySelector("[data-testid='internal-track-link']");
                    const name = nameEl ? nameEl.textContent.trim() : "";

                    const artistEls = row.querySelectorAll("a[data-testid='artist-link']");
                    let artists = Array.from(artistEls).map(a => a.textContent.trim());

                    if (artists.length === 0) {
                        const container = row.querySelector("span[data-testid='artists-container']");
                        if (container) artists = [container.textContent.trim()];
                    }

                    return {name: name, artist: artists.join(", ")};
                """, element)

                if data and data.get("name") and data.get("artist"):
                    tracks.append(Track(name=data["name"], artist=data["artist"]))
            except Exception as exc:
                logger.debug("JS extraction failed for row %d: %s", i + 1, exc)

        return tracks

    def _extract_tracks_selenium(self, row_elements) -> List[Track]:
        """Fallback: extract track data using Selenium element queries."""
        tracks: List[Track] = []
        for i, element in enumerate(row_elements):
            try:
                name_el = element.find_element(By.CSS_SELECTOR, self._selectors.track_link)
                name = name_el.text.strip()

                artist_name = ""
                artist_els = element.find_elements(By.CSS_SELECTOR, self._selectors.artist_link)
                if artist_els:
                    artist_name = ", ".join(el.text.strip() for el in artist_els)
                else:
                    try:
                        container = element.find_element(
                            By.CSS_SELECTOR, self._selectors.artists_container
                        )
                        artist_name = container.text.strip()
                    except Exception:
                        cells = element.find_elements(By.CSS_SELECTOR, "div[role='gridcell']")
                        if len(cells) > 1:
                            artist_name = cells[1].text.strip()

                if name and artist_name:
                    tracks.append(Track(name=name, artist=artist_name))
            except Exception as exc:
                logger.debug("Selenium extraction failed for row %d: %s", i + 1, exc)

        return tracks
