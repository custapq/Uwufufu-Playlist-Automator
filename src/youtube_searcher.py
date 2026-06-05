from __future__ import annotations

import logging
import random
import re
import time
import urllib.parse
from typing import List

import requests

from src.config import AppConfig
from src.exceptions import YouTubeSearchError
from src.models import Track, YoutubeLink
from src.utils.retry import retry

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.youtube.com/results?search_query={query}"
_VIDEO_ID_RE = re.compile(r'watch\?v=([A-Za-z0-9_-]{11})')
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class YouTubeSearcher:
    """Searches YouTube for videos matching Spotify tracks."""

    def __init__(self, config: AppConfig) -> None:
        """Initialise the searcher with application config and an HTTP session."""
        self.config = config
        self._timing = config.timing
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def search_all(self, tracks: List[Track]) -> List[YoutubeLink]:
        """Search YouTube for every track; return one YoutubeLink per track."""
        results: List[YoutubeLink] = []
        total = len(tracks)
        logger.info("Searching YouTube for %d tracks...", total)

        for i, track in enumerate(tracks):
            logger.info("[%d/%d] Searching: %s", i + 1, total, track)
            link = self.search(track)
            results.append(link)
            if i < total - 1:
                delay = random.uniform(
                    self._timing.youtube_search_min,
                    self._timing.youtube_search_max,
                )
                time.sleep(delay)

        found = sum(1 for r in results if r.is_valid)
        logger.info("YouTube search complete: %d/%d found", found, total)
        return results

    @retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
    def search(self, track: Track) -> YoutubeLink:
        """Search YouTube for a single track and return a YoutubeLink."""
        encoded = urllib.parse.quote(track.search_query)
        url = _SEARCH_URL.format(query=encoded)

        response = self._session.get(url)
        response.raise_for_status()

        ids = _VIDEO_ID_RE.findall(response.text)
        unique_ids = list(dict.fromkeys(ids))

        if unique_ids:
            video_url = f"https://www.youtube.com/watch?v={unique_ids[0]}"
            logger.debug("Found: %s → %s", track, video_url)
            return YoutubeLink(track=track, url=video_url)

        logger.warning("No YouTube video found for: %s", track)
        return YoutubeLink(track=track, url=None)
