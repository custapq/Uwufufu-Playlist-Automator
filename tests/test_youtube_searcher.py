from unittest.mock import MagicMock, patch

from src.config import AppConfig
from src.models import Track
from src.youtube_searcher import YouTubeSearcher


def _mock_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp


class TestSearch:
    @patch("requests.Session.get")
    def test_returns_first_unique_id(self, mock_get):
        mock_get.return_value = _mock_response(
            "...watch?v=dQw4w9WgXcQ...watch?v=abc12345678..."
        )
        searcher = YouTubeSearcher(config=AppConfig())
        result = searcher.search(Track(name="Never Gonna Give You Up", artist="Rick Astley"))

        assert result.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result.is_valid is True

    @patch("requests.Session.get")
    def test_deduplicates_preserving_order(self, mock_get):
        # Same ID appears first repeatedly, then a different one
        mock_get.return_value = _mock_response(
            "watch?v=aaaaaaaaaaa watch?v=aaaaaaaaaaa watch?v=bbbbbbbbbbb"
        )
        searcher = YouTubeSearcher(config=AppConfig())
        result = searcher.search(Track(name="X", artist="Y"))
        assert result.url == "https://www.youtube.com/watch?v=aaaaaaaaaaa"

    @patch("requests.Session.get")
    def test_no_results_returns_none(self, mock_get):
        mock_get.return_value = _mock_response("no videos here")
        searcher = YouTubeSearcher(config=AppConfig())
        result = searcher.search(Track(name="Nonexistent", artist="Nobody"))

        assert result.url is None
        assert result.is_valid is False

    @patch("requests.Session.get")
    def test_regex_rejects_non_id_chars(self, mock_get):
        # 'watch?v=' followed by a quote should NOT match (old \S{11} bug)
        mock_get.return_value = _mock_response('watch?v="leadingquote watch?v=GOODid12345')
        searcher = YouTubeSearcher(config=AppConfig())
        result = searcher.search(Track(name="X", artist="Y"))
        assert result.url == "https://www.youtube.com/watch?v=GOODid12345"


class TestSearchAll:
    @patch("src.youtube_searcher.time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_search_all_returns_one_per_track(self, mock_get, _sleep):
        mock_get.return_value = _mock_response("watch?v=dQw4w9WgXcQ")
        searcher = YouTubeSearcher(config=AppConfig())
        tracks = [Track("A", "1"), Track("B", "2"), Track("C", "3")]
        results = searcher.search_all(tracks)

        assert len(results) == 3
        assert all(r.is_valid for r in results)
        assert results[0].track.name == "A"
