import base64
import http.server
import json
import logging
import secrets
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional

import requests

from src.exceptions import SpotifyError
from src.models import ApiCredentials

logger = logging.getLogger(__name__)


class SpotifyUserAuth:
    """Authorization Code flow token manager (reads the user's own playlists).

    Exposes ``get_token()`` so it is a drop-in replacement for
    ``SpotifyTokenManager`` inside ``SpotifyAPI``. The refresh token is cached
    on disk so the interactive browser login is only needed once.
    """

    _AUTH_URL = "https://accounts.spotify.com/authorize"
    _TOKEN_URL = "https://accounts.spotify.com/api/token"
    _SCOPE = "playlist-read-private playlist-read-collaborative"

    def __init__(self, api_creds: ApiCredentials, cache_path: str = ".spotify_token.json") -> None:
        self.client_id = api_creds.spotify_client_id
        self.client_secret = api_creds.spotify_client_secret
        self.redirect_uri = api_creds.spotify_redirect_uri
        self.cache_path = Path(cache_path)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        """Return a valid access token, refreshing or logging in as needed."""
        if self._access_token and time.time() < self._expires_at:
            return self._access_token

        if not self._refresh_token:
            self._refresh_token = self._load_cached_refresh_token()

        if self._refresh_token:
            try:
                self._refresh_access_token()
                return self._access_token or ""
            except SpotifyError:
                logger.warning("Spotify token refresh failed — starting a fresh login.")

        self._authorize()
        return self._access_token or ""

    def login(self, force: bool = False) -> None:
        """Run the interactive browser login (used by ``--spotify-login``)."""
        if force:
            self._clear_cache()
            self._refresh_token = None
            self._access_token = None
        self._authorize()

    # ── token requests ─────────────────────────────────────────────────

    def _basic_header(self) -> dict:
        creds = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        encoded = base64.b64encode(creds).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _token_request(self, data: dict) -> None:
        try:
            response = requests.post(self._TOKEN_URL, headers=self._basic_header(), data=data)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise SpotifyError(f"Spotify token request failed: {exc}") from exc

        self._access_token = payload["access_token"]
        self._expires_at = time.time() + payload.get("expires_in", 3600) - 60
        # A refresh grant may omit refresh_token; keep the existing one if so.
        if payload.get("refresh_token"):
            self._refresh_token = payload["refresh_token"]
        self._save_cache()

    def _exchange_code(self, code: str) -> None:
        self._token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        })

    def _refresh_access_token(self) -> None:
        self._token_request({
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        })

    # ── interactive authorization ──────────────────────────────────────

    def _authorize(self) -> None:
        state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self._SCOPE,
            "state": state,
        }
        auth_url = f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"
        print("Opening your browser to log in to Spotify…")
        print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        code = self._wait_for_callback(state)
        self._exchange_code(code)
        logger.info("Spotify login successful.")

    def _wait_for_callback(self, expected_state: str) -> str:
        parsed = urllib.parse.urlparse(self.redirect_uri)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8888
        result: dict = {}

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                result["code"] = params.get("code", [None])[0]
                result["state"] = params.get("state", [None])[0]
                result["error"] = params.get("error", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<h2>Spotify login complete. You can close this tab.</h2>"
                )

            def log_message(self, *_args) -> None:  # silence the default logging
                pass

        with http.server.HTTPServer((host, port), _Handler) as server:
            server.handle_request()  # serve exactly one callback request

        return self._resolve_callback(result, expected_state)

    @staticmethod
    def _resolve_callback(result: dict, expected_state: str) -> str:
        if result.get("error"):
            raise SpotifyError(f"Spotify authorization denied: {result['error']}")
        if result.get("state") != expected_state:
            raise SpotifyError("State mismatch in Spotify callback (possible CSRF).")
        if not result.get("code"):
            raise SpotifyError("No authorization code returned by Spotify.")
        return result["code"]

    # ── refresh-token cache ────────────────────────────────────────────

    def _save_cache(self) -> None:
        if not self._refresh_token:
            return
        try:
            self.cache_path.write_text(
                json.dumps({"refresh_token": self._refresh_token}), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Could not write Spotify token cache: %s", exc)

    def _load_cached_refresh_token(self) -> Optional[str]:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8")).get("refresh_token")
        except (OSError, json.JSONDecodeError):
            return None

    def _clear_cache(self) -> None:
        try:
            self.cache_path.unlink(missing_ok=True)
        except OSError:
            pass
