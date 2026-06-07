from unittest.mock import patch

import pytest

from src.exceptions import YouTubePlaylistError, YouTubeSearchError
from src.models import ApiCredentials, Track, YoutubeLink
from src.youtube_api import YouTubeAPI


def _api():
    return YouTubeAPI(ApiCredentials(
        spotify_client_id="id",
        spotify_client_secret="secret",
    ))


def _entry(
    title="Song",
    channel="Channel",
    video_id="dQw4w9WgXcQ",
    url=None,
):
    item = {"title": title, "uploader": channel}
    if video_id is not None:
        item["id"] = video_id
    if url is not None:
        item["url"] = url
    return item


def _mock_ydl(mock_ydl_cls, extract_result=None, *, side_effect=None):
    ydl = mock_ydl_cls.return_value.__enter__.return_value
    if side_effect is not None:
        ydl.extract_info.side_effect = side_effect
    else:
        ydl.extract_info.return_value = extract_result
    return ydl


# ─────────────────────────────────────────────
# Phase 2 — search path (track -> YouTube URL)
# ─────────────────────────────────────────────

class TestSearch:
    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_builds_correct_query(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry()]})
        _api().search(Track(name="Song", artist="Artist"))

        ydl = mock_ydl_cls.return_value.__enter__.return_value
        ydl.extract_info.assert_called_once_with("ytsearch1:Song Artist", download=False)

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_returns_link_with_video_url(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(video_id="abc12345678")]})
        link = _api().search(Track(name="X", artist="Y"))

        assert link.url == "https://www.youtube.com/watch?v=abc12345678"
        assert link.is_valid is True
        assert link.track.name == "X"

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_empty_items_returns_none_url(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": []})
        link = _api().search(Track(name="X", artist="Y"))

        assert link.url is None
        assert link.is_valid is False

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_item_missing_video_id_returns_none(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(video_id=None)]})
        link = _api().search(Track(name="X", artist="Y"))
        assert link.url is None


class TestSearchErrors:
    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_error_raises_youtube_search_error(self, mock_ydl_cls):
        ydl = mock_ydl_cls.return_value.__enter__.return_value
        ydl.extract_info.side_effect = Exception("boom")
        with pytest.raises(YouTubeSearchError):
            _api().search(Track(name="X", artist="Y"))
        ydl.extract_info.assert_called_once()


class TestSearchAll:
    @patch("src.youtube_api.YouTubeAPI.search")
    def test_returns_one_link_per_track_in_order(self, mock_search):
        mock_search.side_effect = [
            YoutubeLink(track=Track("A", "1"), url="https://www.youtube.com/watch?v=A"),
            YoutubeLink(track=Track("B", "2"), url="https://www.youtube.com/watch?v=B"),
            YoutubeLink(track=Track("C", "3"), url="https://www.youtube.com/watch?v=C"),
        ]
        tracks = [Track("A", "1"), Track("B", "2"), Track("C", "3")]
        results = _api().search_all(tracks)

        assert len(results) == 3
        assert [r.track.name for r in results] == ["A", "B", "C"]
        assert mock_search.call_count == 3

    @patch("src.youtube_api.YouTubeAPI.search")
    def test_mixes_found_and_not_found(self, mock_search):
        mock_search.side_effect = [
            YoutubeLink(track=Track("A", "1"), url="https://www.youtube.com/watch?v=found123456"),
            YoutubeLink(track=Track("B", "2"), url=None),
        ]
        results = _api().search_all([Track("A", "1"), Track("B", "2")])

        assert results[0].is_valid is True
        assert results[1].is_valid is False

    def test_empty_track_list_returns_empty(self):
        assert _api().search_all([]) == []


# ─────────────────────────────────────────────
# Phase 3 — playlist path (YouTube playlist -> links)
# ─────────────────────────────────────────────

class TestGetPlaylistTracksHappyPath:
    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_calls_extract_info_with_playlist_url(self, mock_ydl_cls):
        playlist_url = "https://www.youtube.com/playlist?list=PLxx"
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(url="https://www.youtube.com/watch?v=v1")]})
        _api().get_playlist_tracks(playlist_url)

        ydl = mock_ydl_cls.return_value.__enter__.return_value
        ydl.extract_info.assert_called_once_with(playlist_url, download=False)

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_uses_video_url_directly(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(url="https://www.youtube.com/watch?v=DIRECT12345")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert links[0].url == "https://www.youtube.com/watch?v=DIRECT12345"

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_maps_title_and_channel(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(title="My Song", channel="My Channel", url="https://www.youtube.com/watch?v=abc")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert links[0].track.name == "My Song"
        assert links[0].track.artist == "My Channel"

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_builds_watch_url_from_video_id(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(video_id="P1", url="P1")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

        assert links[0].url == "https://www.youtube.com/watch?v=P1"


class TestGetPlaylistTracksEdgeAndErrors:
    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_skips_deleted_video(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(title="Deleted video", url="https://www.youtube.com/watch?v=bad"), _entry(title="Real", video_id="ok", url="https://www.youtube.com/watch?v=ok")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_skips_private_video(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(title="Private video", url="https://www.youtube.com/watch?v=bad"), _entry(title="Real", video_id="ok", url="https://www.youtube.com/watch?v=ok")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_skips_item_missing_video_url(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(video_id="no-url"), _entry(title="Real", video_id="ok", url="https://www.youtube.com/watch?v=ok")]})
        links = _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
        assert [l.track.name for l in links] == ["Real"]

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_all_skipped_raises_playlist_error(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, {"entries": [_entry(title="Deleted video", url="https://www.youtube.com/watch?v=bad"), _entry(video_id="missing-url")]})
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_no_data_raises_playlist_error(self, mock_ydl_cls):
        _mock_ydl(mock_ydl_cls, None)
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")

    @patch("src.youtube_api.yt_dlp.YoutubeDL")
    def test_extract_error_raises_playlist_error(self, mock_ydl_cls):
        ydl = mock_ydl_cls.return_value.__enter__.return_value
        ydl.extract_info.side_effect = Exception("offline")
        with pytest.raises(YouTubePlaylistError):
            _api().get_playlist_tracks("https://www.youtube.com/playlist?list=PLxx")
