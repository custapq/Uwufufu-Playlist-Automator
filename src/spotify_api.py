import logging
import re
from typing import List

import requests

from src.exceptions import (
    SpotifyError,
    SpotifyPlaylistAccessError,
    SpotifyPlaylistNotFoundError,
)
from src.models import Track

logger = logging.getLogger(__name__)

_ACCESS_HINT = (
    "Since Spotify's February 2026 API change, only playlists you own or "
    "collaborate on return their tracks. Use --spotify-login with a playlist "
    "you own, or use a YouTube playlist instead."
)

class SpotifyAPI:
    """Fetches track data from a public Spotify playlist using the REST API."""

    def __init__(self, token_manager) -> None:
        """Initialise the API client with any token manager exposing get_token()."""
        self.token_manager = token_manager
        self._session = requests.Session()

    def get_tracks(self, playlist_url: str) -> List[Track]:
        """Return all tracks from the given Spotify playlist URL.

        Raises:
            SpotifyPlaylistNotFoundError: If the URL is invalid or playlist not found.
            SpotifyError: If fetching tracks fails unexpectedly.
        """
        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise SpotifyPlaylistNotFoundError(f"Could not extract a playlist ID from URL: {playlist_url}")

        logger.info(f"Fetching tracks for Spotify playlist ID: {playlist_id}")
        
        tracks: List[Track] = []
        # /items replaces the deprecated /tracks endpoint (Feb 2026 API change).
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/items"
        params = {
            "fields": "items(item(name,artists(name))),next",
            "limit": 100,
            "market": "ES",
        }

        while url:
            data = self._make_request(url, params=params)
            params = None  # Only use params on the first request, 'next' URL has them built-in

            if "items" not in data:
                break

            for item in data["items"]:
                # /items uses the `item` field; fall back to the legacy `track` field.
                track_data = item.get("item") or item.get("track")
                if not track_data:
                    continue

                name = track_data.get("name")
                artists = [a.get("name") for a in track_data.get("artists", []) if a.get("name")]
                artist_str = ", ".join(artists)

                if name and artist_str:
                    tracks.append(Track(name=name, artist=artist_str))

            url = data.get("next")

        if not tracks:
            # Metadata was reachable but no track items came back — the Feb 2026
            # access restriction (playlist not owned by the authenticated user).
            raise SpotifyPlaylistAccessError(
                f"Playlist returned no tracks. {_ACCESS_HINT}"
            )
            
        logger.info("Extracted %d tracks from playlist via API", len(tracks))
        return tracks

    def _extract_playlist_id(self, url: str) -> str:
        """Extract the base-62 playlist ID from a Spotify URL."""
        match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return ""

    def _make_request(self, url: str, params: dict = None) -> dict:
        """Helper to inject the Authorization header and handle basic API errors."""
        token = self.token_manager.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            response = self._session.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            if exc.response is not None:
                if exc.response.status_code == 404:
                    raise SpotifyPlaylistNotFoundError(
                        "Playlist not found. Make sure the URL is correct and the playlist is public."
                    ) from exc
                if exc.response.status_code == 401:
                    raise SpotifyError(
                        "Unauthorized. Make sure your Spotify Client ID and Secret are correct."
                    ) from exc
                if exc.response.status_code == 403:
                    raise SpotifyPlaylistAccessError(
                        f"Forbidden (403) reading playlist tracks. {_ACCESS_HINT}"
                    ) from exc
            raise SpotifyError(f"Failed to fetch data from Spotify API: {exc}") from exc
        except requests.RequestException as exc:
            raise SpotifyError(f"Network error while connecting to Spotify API: {exc}") from exc
