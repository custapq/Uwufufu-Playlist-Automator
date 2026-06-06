from unittest.mock import patch

import pytest
import requests

from src.exceptions import YouTubeSearchError
from src.models import ApiCredentials, Track
from src.youtube_api import YouTubeAPI

from tests.conftest import make_response


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
    def test_http_error_raises_youtube_search_error(self, mock_get):
        # raise_for_status -> HTTPError is converted immediately (no retry)
        mock_get.return_value = make_response({}, status=500)
        with pytest.raises(YouTubeSearchError):
            _api().search(Track(name="X", artist="Y"))
        assert mock_get.call_count == 1

    @patch("requests.Session.get")
    def test_network_error_retries_then_raises(self, mock_get):
        # session.get itself raising is outside the try/except, so the @retry
        # decorator retries and ultimately re-raises the raw RequestException.
        mock_get.side_effect = requests.ConnectionError("offline")
        with pytest.raises(requests.RequestException):
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
