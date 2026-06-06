import logging
from typing import List
from urllib.parse import parse_qs, urlparse

import requests

from src.exceptions import YouTubePlaylistError, YouTubeSearchError
from src.models import Track, YoutubeLink, ApiCredentials
from src.utils.retry import retry

logger = logging.getLogger(__name__)

_DELETED_TITLES = {"Deleted video", "Private video"}


class YouTubeAPI:
    """Fetches YouTube playlist tracks and searches for videos via the REST API."""

    _SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    _PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

    def __init__(self, api_creds: ApiCredentials) -> None:
        """Initialise the API client with credentials."""
        self.api_key = api_creds.youtube_api_key
        self._session = requests.Session()

    def get_playlist_tracks(self, playlist_url: str) -> List[YoutubeLink]:
        """Return all videos from a public YouTube playlist as YoutubeLink objects.

        Each video's URL is taken directly from the playlist — no extra search needed.

        Raises:
            YouTubePlaylistError: If the playlist ID cannot be extracted or the API returns an error.
        """
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise YouTubePlaylistError(
                f"Could not extract a playlist ID from URL: {playlist_url}"
            )

        logger.info("Fetching videos from YouTube playlist ID: %s", playlist_id)

        links: List[YoutubeLink] = []
        params: dict = {
            "part": "snippet",
            "maxResults": 50,
            "playlistId": playlist_id,
            "key": self.api_key,
        }
        page_token: str | None = None

        while True:
            if page_token:
                params["pageToken"] = page_token

            try:
                response = self._session.get(self._PLAYLIST_ITEMS_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    raise YouTubePlaylistError(
                        "YouTube playlist not found. Make sure the URL is correct and the playlist is public."
                    ) from exc
                if status == 403:
                    raise YouTubePlaylistError(
                        "Access denied (403). The playlist may be private or your API key lacks permissions."
                    ) from exc
                raise YouTubePlaylistError(f"YouTube API error: {exc}") from exc
            except requests.RequestException as exc:
                raise YouTubePlaylistError(f"Network error while fetching YouTube playlist: {exc}") from exc

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                title = snippet.get("title", "")
                channel = snippet.get("videoOwnerChannelTitle", "")
                video_id = snippet.get("resourceId", {}).get("videoId")

                if not video_id or title in _DELETED_TITLES:
                    continue

                url = f"https://www.youtube.com/watch?v={video_id}"
                links.append(YoutubeLink(track=Track(name=title, artist=channel), url=url))

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        if not links:
            raise YouTubePlaylistError("Playlist was found but returned no playable videos.")

        logger.info("Extracted %d videos from YouTube playlist", len(links))
        return links

    @staticmethod
    def _extract_playlist_id(url: str) -> str:
        """Extract the playlist ID from a YouTube playlist URL (query param 'list')."""
        qs = parse_qs(urlparse(url).query)
        ids = qs.get("list", [])
        return ids[0] if ids else ""

    def search_all(self, tracks: List[Track]) -> List[YoutubeLink]:
        """Search YouTube for every track; return one YoutubeLink per track."""
        results: List[YoutubeLink] = []
        total = len(tracks)
        logger.info("Searching YouTube for %d tracks via API...", total)

        for i, track in enumerate(tracks):
            logger.info("[%d/%d] Searching: %s", i + 1, total, track)
            link = self.search(track)
            results.append(link)

        found = sum(1 for r in results if r.is_valid)
        logger.info("YouTube API search complete: %d/%d found", found, total)
        return results

    def search(self, track: Track) -> YoutubeLink:
        """Search YouTube for a single track and return a YoutubeLink.

        Raises:
            YouTubeSearchError: If the request keeps failing after retries
                (network error or HTTP error response).
        """
        try:
            data = self._search_request(track)
        except requests.RequestException as exc:
            text = getattr(getattr(exc, "response", None), "text", None)
            logger.error("YouTube API search failed: %s", text or exc)
            raise YouTubeSearchError(f"YouTube API request failed: {exc}") from exc

        items = data.get("items", [])
        if items:
            video_id = items[0].get("id", {}).get("videoId")
            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.debug("Found: %s → %s", track, video_url)
                return YoutubeLink(track=track, url=video_url)

        logger.warning("No YouTube video found for: %s", track)
        return YoutubeLink(track=track, url=None)

    @retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
    def _search_request(self, track: Track) -> dict:
        """Perform the search HTTP request, retrying on any request error.

        Both connection errors and HTTP error responses (``raise_for_status``)
        are ``requests.RequestException`` subclasses, so the ``@retry`` decorator
        retries them; the final failure propagates to :meth:`search` to be
        wrapped as a ``YouTubeSearchError``.
        """
        params = {
            "part": "snippet",
            "maxResults": 1,
            "q": track.search_query,
            "type": "video",
            "key": self.api_key,
        }
        response = self._session.get(self._SEARCH_URL, params=params)
        response.raise_for_status()
        return response.json()
