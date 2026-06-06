from unittest.mock import MagicMock, patch

import pytest
import requests

from src.exceptions import SpotifyError, SpotifyPlaylistNotFoundError
from src.spotify_api import SpotifyAPI

from tests.conftest import make_response


def _api(token="tok"):
    token_manager = MagicMock()
    token_manager.get_token.return_value = token
    return SpotifyAPI(token_manager)


def _item(name="Song", artists=("Artist",)):
    return {"track": {"name": name, "artists": [{"name": a} for a in artists]}}


class TestExtractPlaylistId:
    def test_extracts_from_standard_url(self):
        api = _api()
        assert api._extract_playlist_id(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        ) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_extracts_with_query_params(self):
        api = _api()
        assert api._extract_playlist_id(
            "https://open.spotify.com/playlist/ABC123?si=xyz"
        ) == "ABC123"

    def test_returns_empty_for_non_playlist_url(self):
        api = _api()
        assert api._extract_playlist_id("https://open.spotify.com/track/ABC") == ""

    def test_returns_empty_for_spotify_uri(self):
        # The current regex only matches 'playlist/<id>', not the 'spotify:playlist:<id>' URI form
        api = _api()
        assert api._extract_playlist_id("spotify:playlist:ABC") == ""


class TestGetTracksHappyPath:
    @patch("requests.Session.get")
    def test_single_page_parses_tracks(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_item("A", ("X",)), _item("B", ("Y",))], "next": None}
        )
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")

        assert len(tracks) == 2
        assert tracks[0].name == "A" and tracks[0].artist == "X"
        assert tracks[1].name == "B" and tracks[1].artist == "Y"

    @patch("requests.Session.get")
    def test_joins_multiple_artists(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_item("Song", ("A", "B", "C"))], "next": None}
        )
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")
        assert tracks[0].artist == "A, B, C"

    @patch("requests.Session.get")
    def test_calls_correct_endpoint(self, mock_get):
        # Guards against the old hardcoded-playlist-id bug
        mock_get.return_value = make_response({"items": [_item()], "next": None})
        _api().get_tracks("https://open.spotify.com/playlist/MYID42")

        called_url = mock_get.call_args.args[0]
        assert called_url == "https://api.spotify.com/v1/playlists/MYID42/tracks"

    @patch("requests.Session.get")
    def test_first_request_sends_fields_and_market_and_limit(self, mock_get):
        # Guards against the old fields bug (missing artists / next)
        mock_get.return_value = make_response({"items": [_item()], "next": None})
        _api().get_tracks("https://open.spotify.com/playlist/abc")

        params = mock_get.call_args.kwargs["params"]
        assert "artists(name)" in params["fields"]
        assert "next" in params["fields"]
        assert params["market"] == "ES"
        assert params["limit"] == 100

    @patch("requests.Session.get")
    def test_pagination_follows_next_url(self, mock_get):
        mock_get.side_effect = [
            make_response({"items": [_item("P1")], "next": "https://api.spotify.com/next-page"}),
            make_response({"items": [_item("P2")], "next": None}),
        ]
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")

        assert [t.name for t in tracks] == ["P1", "P2"]
        assert mock_get.call_count == 2
        assert mock_get.call_args_list[1].args[0] == "https://api.spotify.com/next-page"

    @patch("requests.Session.get")
    def test_params_none_on_subsequent_request(self, mock_get):
        mock_get.side_effect = [
            make_response({"items": [_item("P1")], "next": "https://api.spotify.com/next-page"}),
            make_response({"items": [_item("P2")], "next": None}),
        ]
        _api().get_tracks("https://open.spotify.com/playlist/abc")

        # First request carries params, the 'next' request must not re-send them
        assert mock_get.call_args_list[0].kwargs["params"] is not None
        assert mock_get.call_args_list[1].kwargs["params"] is None

    @patch("requests.Session.get")
    def test_stops_when_next_is_null(self, mock_get):
        mock_get.return_value = make_response({"items": [_item()], "next": None})
        _api().get_tracks("https://open.spotify.com/playlist/abc")
        assert mock_get.call_count == 1


class TestGetTracksEdgeAndErrors:
    def test_invalid_url_raises_playlist_not_found(self):
        with pytest.raises(SpotifyPlaylistNotFoundError):
            _api().get_tracks("https://open.spotify.com/track/not-a-playlist")

    @patch("requests.Session.get")
    def test_skips_null_track_items(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [{"track": None}, _item("Real")], "next": None}
        )
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")
        assert [t.name for t in tracks] == ["Real"]

    @patch("requests.Session.get")
    def test_skips_track_missing_name(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [{"track": {"name": "", "artists": [{"name": "X"}]}}, _item("Real")],
             "next": None}
        )
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")
        assert [t.name for t in tracks] == ["Real"]

    @patch("requests.Session.get")
    def test_skips_track_missing_artist(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [{"track": {"name": "NoArtist", "artists": []}}, _item("Real")],
             "next": None}
        )
        tracks = _api().get_tracks("https://open.spotify.com/playlist/abc")
        assert [t.name for t in tracks] == ["Real"]

    @patch("requests.Session.get")
    def test_empty_playlist_raises_spotify_error(self, mock_get):
        mock_get.return_value = make_response({"items": [], "next": None})
        with pytest.raises(SpotifyError):
            _api().get_tracks("https://open.spotify.com/playlist/abc")

    @patch("requests.Session.get")
    def test_no_items_key_breaks_gracefully(self, mock_get):
        mock_get.return_value = make_response({"next": None})
        with pytest.raises(SpotifyError):
            _api().get_tracks("https://open.spotify.com/playlist/abc")


class TestMakeRequestErrors:
    @patch("requests.Session.get")
    def test_404_raises_playlist_not_found(self, mock_get):
        mock_get.return_value = make_response({}, status=404)
        with pytest.raises(SpotifyPlaylistNotFoundError):
            _api().get_tracks("https://open.spotify.com/playlist/abc")

    @patch("requests.Session.get")
    def test_401_raises_spotify_error(self, mock_get):
        mock_get.return_value = make_response({}, status=401)
        with pytest.raises(SpotifyError):
            _api().get_tracks("https://open.spotify.com/playlist/abc")

    @patch("requests.Session.get")
    def test_403_raises_spotify_error_with_body(self, mock_get):
        mock_get.return_value = make_response({}, status=403, text="region locked")
        with pytest.raises(SpotifyError, match="region locked"):
            _api().get_tracks("https://open.spotify.com/playlist/abc")

    @patch("requests.Session.get")
    def test_network_error_raises_spotify_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("offline")
        with pytest.raises(SpotifyError):
            _api().get_tracks("https://open.spotify.com/playlist/abc")

    @patch("requests.Session.get")
    def test_injects_bearer_token_header(self, mock_get):
        mock_get.return_value = make_response({"items": [_item()], "next": None})
        _api(token="secret-token").get_tracks("https://open.spotify.com/playlist/abc")

        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer secret-token"
