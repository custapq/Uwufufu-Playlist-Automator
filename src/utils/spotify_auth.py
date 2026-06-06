import base64
import logging
import time
from typing import Optional

import requests

from src.exceptions import SpotifyError
from src.models import ApiCredentials

logger = logging.getLogger(__name__)

class SpotifyTokenManager:
    """Manages Spotify API Access Tokens using the Client Credentials Flow."""

    _TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, api_creds: ApiCredentials) -> None:
        self.client_id = api_creds.spotify_client_id
        self.client_secret = api_creds.spotify_client_secret
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        """Return a valid access token, fetching a new one if necessary."""
        if self._access_token and time.time() < self._expires_at:
            return self._access_token
        
        self._fetch_new_token()
        # _fetch_new_token sets self._access_token
        # It's guaranteed to be not None if it succeeds
        return self._access_token or ""

    def _fetch_new_token(self) -> None:
        """Request a new access token from Spotify."""
        logger.debug("Fetching new Spotify access token...")
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(self._TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            self._access_token = token_data["access_token"]
            # buffer 60 seconds to ensure we don't return a token about to expire
            self._expires_at = time.time() + token_data["expires_in"] - 60
            logger.info("Successfully authenticated with Spotify API.")
        except requests.RequestException as exc:
            raise SpotifyError(f"Failed to authenticate with Spotify API: {exc}") from exc
