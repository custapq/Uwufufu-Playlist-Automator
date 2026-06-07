import base64
import time
from unittest.mock import patch

import pytest
import requests

from src.exceptions import SpotifyError
from src.models import ApiCredentials
from src.utils.spotify_auth import SpotifyTokenManager

from tests.conftest import make_response


def _creds(client_id="my_id", client_secret="my_secret"):
    return ApiCredentials(
        spotify_client_id=client_id,
        spotify_client_secret=client_secret,
    )


def _token_payload(token="tok123", expires_in=3600):
    return {"access_token": token, "expires_in": expires_in}


class TestGetToken:
    @patch("requests.post")
    def test_fetches_new_token_when_none_cached(self, mock_post):
        mock_post.return_value = make_response(_token_payload("fresh_token"))
        mgr = SpotifyTokenManager(_creds())

        token = mgr.get_token()

        assert token == "fresh_token"
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == SpotifyTokenManager._TOKEN_URL

    @patch("requests.post")
    def test_returns_cached_token_when_valid(self, mock_post):
        mock_post.return_value = make_response(_token_payload("cached"))
        mgr = SpotifyTokenManager(_creds())

        first = mgr.get_token()
        second = mgr.get_token()

        assert first == second == "cached"
        mock_post.assert_called_once()  # no second network call

    @patch("requests.post")
    def test_refetches_when_expired(self, mock_post):
        mock_post.side_effect = [
            make_response(_token_payload("old")),
            make_response(_token_payload("new")),
        ]
        mgr = SpotifyTokenManager(_creds())

        first = mgr.get_token()
        mgr._expires_at = time.time() - 1  # force expiry
        second = mgr.get_token()

        assert first == "old"
        assert second == "new"
        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_expiry_buffer_60s_applied(self, mock_post):
        mock_post.return_value = make_response(_token_payload(expires_in=3600))
        mgr = SpotifyTokenManager(_creds())

        before = time.time()
        mgr.get_token()
        # expires_at = now + 3600 - 60 buffer
        assert mgr._expires_at == pytest.approx(before + 3540, abs=2)

    @patch("requests.post")
    def test_authorization_header_is_basic_base64(self, mock_post):
        mock_post.return_value = make_response(_token_payload())
        mgr = SpotifyTokenManager(_creds("abc", "xyz"))

        mgr.get_token()

        headers = mock_post.call_args.kwargs["headers"]
        expected = base64.b64encode(b"abc:xyz").decode("utf-8")
        assert headers["Authorization"] == f"Basic {expected}"

    @patch("requests.post")
    def test_grant_type_client_credentials_in_body(self, mock_post):
        mock_post.return_value = make_response(_token_payload())
        mgr = SpotifyTokenManager(_creds())

        mgr.get_token()

        data = mock_post.call_args.kwargs["data"]
        assert data == {"grant_type": "client_credentials"}

    @patch("requests.post")
    def test_request_exception_raises_spotify_error(self, mock_post):
        mock_post.side_effect = requests.RequestException("boom")
        mgr = SpotifyTokenManager(_creds())

        with pytest.raises(SpotifyError):
            mgr.get_token()

    def test_get_token_returns_empty_string_guard(self):
        # If _fetch_new_token leaves _access_token None, the `or ""` guard kicks in
        mgr = SpotifyTokenManager(_creds())
        with patch.object(mgr, "_fetch_new_token", return_value=None):
            assert mgr.get_token() == ""
