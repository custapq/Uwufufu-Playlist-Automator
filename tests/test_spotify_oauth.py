"""Tests for SpotifyUserAuth (Authorization Code flow token manager)."""

import base64
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from src.exceptions import SpotifyError
from src.models import ApiCredentials
from src.utils.spotify_oauth import SpotifyUserAuth

from tests.conftest import make_response


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _creds(
    client_id: str = "cid",
    client_secret: str = "csec",
    redirect_uri: str = "http://127.0.0.1:8888/callback",
) -> ApiCredentials:
    return ApiCredentials(
        spotify_client_id=client_id,
        spotify_client_secret=client_secret,
        spotify_redirect_uri=redirect_uri,
    )


def _auth(tmp_path: Path, **cred_kwargs) -> SpotifyUserAuth:
    """Return a SpotifyUserAuth with its cache pointing to a temp file."""
    cache = tmp_path / ".spotify_token.json"
    return SpotifyUserAuth(_creds(**cred_kwargs), cache_path=str(cache))


def _token_payload(
    access_token: str = "access_tok",
    expires_in: int = 3600,
    refresh_token: str | None = "refresh_tok",
) -> dict:
    payload: dict = {"access_token": access_token, "expires_in": expires_in}
    if refresh_token is not None:
        payload["refresh_token"] = refresh_token
    return payload


# ─────────────────────────────────────────────
# get_token() — routing logic
# ─────────────────────────────────────────────

class TestGetToken:
    def test_returns_cached_token_when_valid(self, tmp_path):
        auth = _auth(tmp_path)
        auth._access_token = "cached"
        auth._expires_at = time.time() + 3600

        token = auth.get_token()

        assert token == "cached"

    @patch("requests.post")
    def test_uses_cached_refresh_token_without_browser(self, mock_post, tmp_path):
        """If a refresh token is cached on disk, it should refresh silently."""
        cache = tmp_path / ".spotify_token.json"
        cache.write_text(json.dumps({"refresh_token": "r_tok"}), encoding="utf-8")

        mock_post.return_value = make_response(_token_payload("new_access"))
        auth = SpotifyUserAuth(_creds(), cache_path=str(cache))

        token = auth.get_token()

        assert token == "new_access"
        # No browser interaction (webbrowser.open / HTTPServer) should have been called
        mock_post.assert_called_once()
        data = mock_post.call_args.kwargs["data"]
        assert data["grant_type"] == "refresh_token"

    def test_calls_authorize_when_no_refresh_token_cached(self, tmp_path):
        auth = _auth(tmp_path)

        with patch.object(auth, "_authorize") as mock_auth:
            auth._access_token = None
            auth._refresh_token = None
            auth.get_token()
            mock_auth.assert_called_once()

    @patch("requests.post")
    def test_falls_back_to_authorize_when_refresh_fails(self, mock_post, tmp_path):
        """If refresh raises SpotifyError, get_token() should fall back to authorize."""
        cache = tmp_path / ".spotify_token.json"
        cache.write_text(json.dumps({"refresh_token": "bad_tok"}), encoding="utf-8")

        mock_post.side_effect = requests.RequestException("network error")
        auth = SpotifyUserAuth(_creds(), cache_path=str(cache))

        with patch.object(auth, "_authorize") as mock_auth:
            auth.get_token()
            mock_auth.assert_called_once()

    def test_returns_empty_string_guard_when_access_token_none(self, tmp_path):
        auth = _auth(tmp_path)
        with patch.object(auth, "_authorize", return_value=None):
            result = auth.get_token()
        assert result == ""


# ─────────────────────────────────────────────
# _token_request() — POST mechanics
# ─────────────────────────────────────────────

class TestTokenRequest:
    @patch("requests.post")
    def test_exchange_code_sends_correct_body(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload())
        auth = _auth(tmp_path)

        auth._exchange_code("auth_code_123")

        data = mock_post.call_args.kwargs["data"]
        assert data == {
            "grant_type": "authorization_code",
            "code": "auth_code_123",
            "redirect_uri": "http://127.0.0.1:8888/callback",
        }

    @patch("requests.post")
    def test_refresh_sends_correct_body(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload())
        auth = _auth(tmp_path)
        auth._refresh_token = "old_refresh"

        auth._refresh_access_token()

        data = mock_post.call_args.kwargs["data"]
        assert data == {
            "grant_type": "refresh_token",
            "refresh_token": "old_refresh",
        }

    @patch("requests.post")
    def test_basic_auth_header_is_base64_of_id_and_secret(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload())
        auth = _auth(tmp_path, client_id="my_id", client_secret="my_secret")

        auth._exchange_code("code")

        headers = mock_post.call_args.kwargs["headers"]
        expected = base64.b64encode(b"my_id:my_secret").decode()
        assert headers["Authorization"] == f"Basic {expected}"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

    @patch("requests.post")
    def test_stores_access_token(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload("shiny_token"))
        auth = _auth(tmp_path)

        auth._exchange_code("code")

        assert auth._access_token == "shiny_token"

    @patch("requests.post")
    def test_expiry_buffer_60s_applied(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload(expires_in=3600))
        auth = _auth(tmp_path)
        before = time.time()

        auth._exchange_code("code")

        assert auth._expires_at == pytest.approx(before + 3540, abs=2)

    @patch("requests.post")
    def test_updates_refresh_token_when_provided_in_response(self, mock_post, tmp_path):
        mock_post.return_value = make_response(
            _token_payload(refresh_token="brand_new_refresh")
        )
        auth = _auth(tmp_path)

        auth._exchange_code("code")

        assert auth._refresh_token == "brand_new_refresh"

    @patch("requests.post")
    def test_keeps_existing_refresh_when_absent_in_response(self, mock_post, tmp_path):
        """Refresh grants may omit the refresh_token; existing one must be kept."""
        mock_post.return_value = make_response(
            _token_payload(refresh_token=None)  # no refresh_token in payload
        )
        auth = _auth(tmp_path)
        auth._refresh_token = "existing_refresh"

        auth._refresh_access_token()

        assert auth._refresh_token == "existing_refresh"

    @patch("requests.post")
    def test_request_exception_raises_spotify_error(self, mock_post, tmp_path):
        mock_post.side_effect = requests.RequestException("boom")
        auth = _auth(tmp_path)

        with pytest.raises(SpotifyError, match="token request failed"):
            auth._exchange_code("code")

    @patch("requests.post")
    def test_token_url_is_spotify_endpoint(self, mock_post, tmp_path):
        mock_post.return_value = make_response(_token_payload())
        auth = _auth(tmp_path)

        auth._exchange_code("code")

        assert mock_post.call_args.args[0] == SpotifyUserAuth._TOKEN_URL


# ─────────────────────────────────────────────
# _resolve_callback() — static parsing
# ─────────────────────────────────────────────

class TestResolveCallback:
    def test_valid_callback_returns_code(self):
        result = {"code": "abc123", "state": "s", "error": None}
        code = SpotifyUserAuth._resolve_callback(result, expected_state="s")
        assert code == "abc123"

    def test_error_in_callback_raises_spotify_error(self):
        result = {"code": None, "state": "s", "error": "access_denied"}
        with pytest.raises(SpotifyError, match="access_denied"):
            SpotifyUserAuth._resolve_callback(result, expected_state="s")

    def test_state_mismatch_raises_spotify_error(self):
        result = {"code": "abc", "state": "wrong", "error": None}
        with pytest.raises(SpotifyError, match="State mismatch"):
            SpotifyUserAuth._resolve_callback(result, expected_state="expected")

    def test_missing_code_raises_spotify_error(self):
        result = {"code": None, "state": "s", "error": None}
        with pytest.raises(SpotifyError, match="No authorization code"):
            SpotifyUserAuth._resolve_callback(result, expected_state="s")


# ─────────────────────────────────────────────
# Token cache — save / load / clear
# ─────────────────────────────────────────────

class TestTokenCache:
    def test_save_cache_writes_refresh_token(self, tmp_path):
        auth = _auth(tmp_path)
        auth._refresh_token = "saved_refresh"

        auth._save_cache()

        data = json.loads(auth.cache_path.read_text(encoding="utf-8"))
        assert data == {"refresh_token": "saved_refresh"}

    def test_save_cache_skips_when_no_refresh_token(self, tmp_path):
        auth = _auth(tmp_path)
        auth._refresh_token = None

        auth._save_cache()

        assert not auth.cache_path.exists()

    def test_load_cache_reads_refresh_token(self, tmp_path):
        auth = _auth(tmp_path)
        auth.cache_path.write_text(
            json.dumps({"refresh_token": "loaded_refresh"}), encoding="utf-8"
        )

        result = auth._load_cached_refresh_token()

        assert result == "loaded_refresh"

    def test_load_cache_returns_none_when_file_missing(self, tmp_path):
        auth = _auth(tmp_path)
        # cache_path does not exist yet

        assert auth._load_cached_refresh_token() is None

    def test_load_cache_returns_none_on_invalid_json(self, tmp_path):
        auth = _auth(tmp_path)
        auth.cache_path.write_text("not json!!!", encoding="utf-8")

        assert auth._load_cached_refresh_token() is None

    def test_clear_cache_removes_file(self, tmp_path):
        auth = _auth(tmp_path)
        auth.cache_path.write_text("{}", encoding="utf-8")

        auth._clear_cache()

        assert not auth.cache_path.exists()

    def test_clear_cache_is_idempotent_when_file_missing(self, tmp_path):
        auth = _auth(tmp_path)
        # File does not exist — should not raise
        auth._clear_cache()


# ─────────────────────────────────────────────
# login() — public interactive entry-point
# ─────────────────────────────────────────────

class TestLogin:
    def test_login_force_clears_cache_and_runs_authorize(self, tmp_path):
        auth = _auth(tmp_path)
        auth.cache_path.write_text(json.dumps({"refresh_token": "old"}), encoding="utf-8")
        auth._refresh_token = "old"
        auth._access_token = "old_access"

        with patch.object(auth, "_authorize") as mock_auth:
            auth.login(force=True)

        mock_auth.assert_called_once()
        assert not auth.cache_path.exists()
        assert auth._refresh_token is None
        assert auth._access_token is None

    def test_login_without_force_does_not_clear_cache(self, tmp_path):
        auth = _auth(tmp_path)
        auth.cache_path.write_text(json.dumps({"refresh_token": "kept"}), encoding="utf-8")

        with patch.object(auth, "_authorize"):
            auth.login(force=False)

        assert auth.cache_path.exists()

    def test_login_without_force_runs_authorize(self, tmp_path):
        auth = _auth(tmp_path)

        with patch.object(auth, "_authorize") as mock_auth:
            auth.login(force=False)

        mock_auth.assert_called_once()
