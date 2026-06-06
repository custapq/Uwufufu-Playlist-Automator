from unittest.mock import patch

import pytest
import requests

from src.exceptions import YouTubePlaylistError, YouTubeSearchError
from src.models import ApiCredentials, Track
from src.youtube_api import YouTubeAPI

from tests.conftest import make_response


def _pl_item(title="Song", channel="Channel", video_id="vid12345678"):
    snippet = {"title": title, "videoOwnerChannelTitle": channel}
    if video_id is not None:
        snippet["resourceId"] = {"videoId": video_id}
    return {"snippet": snippet}


def _api(key="yt_key"):
    return YouTubeAPI(ApiCredentials(
        spotify_client_id="id",
        spotify_client_secret="secret",
        youtube_api_key=key,
    ))


def _search_hit(video_id="dQw4w9WgXcQ"):
    return {"items": [{"id": {"videoId": video_id}}]}


# ─────────────────────────────────────────────
# Phase 2 — search path (track -> YouTube URL)
# ─────────────────────────────────────────────

class TestSearch:
    @patch("requests.Session.get")
    def test_builds_correct_params(self, mock_get):
        mock_get.return_value = make_response(_search_hit())
        _api("the_key").search(Track(name="Song", artist="Artist"))

        params = mock_get.call_args.kwargs["params"]
        assert params["part"] == "snippet"
        assert params["maxResults"] == 1
        assert params["q"] == "Song Artist"
        assert params["type"] == "video"
        assert params["key"] == "the_key"

    @patch("requests.Session.get")
    def test_returns_link_with_video_url(self, mock_get):
        mock_get.return_value = make_response(_search_hit("abc12345678"))
        link = _api().search(Track(name="X", artist="Y"))

        assert link.url == "https://www.youtube.com/watch?v=abc12345678"
        assert link.is_valid is True
        assert link.track.name == "X"

    @patch("requests.Session.get")
    def test_empty_items_returns_none_url(self, mock_get):
        mock_get.return_value = make_response({"items": []})
        link = _api().search(Track(name="X", artist="Y"))

        assert link.url is None
        assert link.is_valid is False

    @patch("requests.Session.get")
    def test_item_missing_video_id_returns_none(self, mock_get):
        mock_get.return_value = make_response({"items": [{"id": {}}]})
        link = _api().search(Track(name="X", artist="Y"))
        assert link.url is None


class TestSearchErrors:
    @patch("requests.Session.get")
    def test_http_error_retries_then_raises_youtube_search_error(self, mock_get):
        # HTTPError is a RequestException subclass -> retried 3x, then wrapped
        mock_get.return_value = make_response({}, status=500)
        with pytest.raises(YouTubeSearchError):
            _api().search(Track(name="X", artist="Y"))
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_network_error_retries_then_raises_youtube_search_error(self, mock_get):
        # A connection error is retried 3x and wrapped as YouTubeSearchError so
        # main()'s UwufufuError handler can catch it (no raw exception escapes).
        mock_get.side_effect = requests.ConnectionError("offline")
        with pytest.raises(YouTubeSearchError):
            _api().search(Track(name="X", artist="Y"))
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_retry_succeeds_on_second_attempt(self, mock_get):
        mock_get.side_effect = [
            requests.ConnectionError("blip"),
            make_response(_search_hit("vid12345678")),
        ]
        link = _api().search(Track(name="X", artist="Y"))

        assert link.url == "https://www.youtube.com/watch?v=vid12345678"
        assert mock_get.call_count == 2


class TestSearchAll:
    @patch("requests.Session.get")
    def test_returns_one_link_per_track_in_order(self, mock_get):
        mock_get.return_value = make_response(_search_hit())
        tracks = [Track("A", "1"), Track("B", "2"), Track("C", "3")]
        results = _api().search_all(tracks)

        assert len(results) == 3
        assert [r.track.name for r in results] == ["A", "B", "C"]
        assert all(r.is_valid for r in results)

    @patch("requests.Session.get")
    def test_mixes_found_and_not_found(self, mock_get):
        mock_get.side_effect = [
            make_response(_search_hit("found123456")),
            make_response({"items": []}),
        ]
        results = _api().search_all([Track("A", "1"), Track("B", "2")])

        assert results[0].is_valid is True
        assert results[1].is_valid is False

    def test_empty_track_list_returns_empty(self):
        assert _api().search_all([]) == []


# ─────────────────────────────────────────────
# Phase 3 — playlist path (YouTube playlist -> links)
# ─────────────────────────────────────────────

class TestExtractPlaylistId:
    def test_extracts_from_playlist_url(self):
        assert YouTubeAPI._extract_playlist_id(
            "https://www.youtube.com/playlist?list=PLabc123"
        ) == "PLabc123"

    def test_extracts_from_watch_with_list(self):
        assert YouTubeAPI._extract_playlist_id(
            "https://www.youtube.com/watch?v=xyz&list=PLdef456"
        ) == "PLdef456"

    def test_returns_empty_when_no_list_param(self):
        assert YouTubeAPI._extract_playlist_id("https://www.youtube.com/watch?v=xyz") == ""


class TestGetPlaylistTracksHappyPath:
    @patch("requests.Session.get")
    def test_single_page_builds_correct_params(self, mock_get):
        mock_get.return_value = make_response({"items": [_pl_item()]})
        _api("the_key").get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        url = mock_get.call_args.args[0]
        params = mock_get.call_args.kwargs["params"]
        assert url == YouTubeAPI._PLAYLIST_ITEMS_URL
        assert params["part"] == "snippet"
        assert params["maxResults"] == 50
        assert params["playlistId"] == "PLxx"
        assert params["key"] == "the_key"

    @patch("requests.Session.get")
    def test_uses_video_url_directly(self, mock_get):
        # Must build the URL from resourceId.videoId, never hitting the search endpoint
        mock_get.return_value = make_response({"items": [_pl_item(video_id="DIRECT12345")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert links[0].url == "https://www.youtube.com/watch?v=DIRECT12345"
        # only the playlistItems endpoint was called
        assert all(c.args[0] == YouTubeAPI._PLAYLIST_ITEMS_URL for c in mock_get.call_args_list)

    @patch("requests.Session.get")
    def test_maps_title_and_channel(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_pl_item(title="My Song", channel="My Channel")]}
        )
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert links[0].track.name == "My Song"
        assert links[0].track.artist == "My Channel"

    @patch("requests.Session.get")
    def test_pagination_follows_next_page_token(self, mock_get):
        mock_get.side_effect = [
            make_response({"items": [_pl_item(title="P1")], "nextPageToken": "TOKEN2"}),
            make_response({"items": [_pl_item(title="P2")]}),
        ]
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert [l.track.name for l in links] == ["P1", "P2"]
        assert mock_get.call_count == 2
        assert mock_get.call_args_list[1].kwargs["params"]["pageToken"] == "TOKEN2"

    @patch("requests.Session.get")
    def test_stops_when_no_next_page_token(self, mock_get):
        mock_get.return_value = make_response({"items": [_pl_item()]})
        _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert mock_get.call_count == 1


class TestGetPlaylistTracksEdgeAndErrors:
    def test_invalid_url_raises_playlist_error(self):
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/watch?v=no-list")

    @patch("requests.Session.get")
    def test_skips_deleted_video(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_pl_item(title="Deleted video"), _pl_item(title="Real")]}
        )
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("requests.Session.get")
    def test_skips_private_video(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_pl_item(title="Private video"), _pl_item(title="Real")]}
        )
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("requests.Session.get")
    def test_skips_item_missing_video_id(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_pl_item(video_id=None), _pl_item(title="Real")]}
        )
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("requests.Session.get")
    def test_all_skipped_raises_playlist_error(self, mock_get):
        mock_get.return_value = make_response(
            {"items": [_pl_item(title="Deleted video"), _pl_item(video_id=None)]}
        )
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("requests.Session.get")
    def test_404_raises_playlist_error_not_found(self, mock_get):
        mock_get.return_value = make_response({}, status=404)
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("requests.Session.get")
    def test_403_raises_playlist_error_access_denied(self, mock_get):
        mock_get.return_value = make_response({}, status=403)
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("requests.Session.get")
    def test_other_http_error_raises_playlist_error(self, mock_get):
        mock_get.return_value = make_response({}, status=500)
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("requests.Session.get")
    def test_network_error_raises_playlist_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("offline")
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
