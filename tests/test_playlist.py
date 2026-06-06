import pytest

from src.exceptions import InvalidInputError
from src.utils.playlist import detect_source


class TestDetectSource:
    def test_spotify_open_url(self):
        assert detect_source("https://open.spotify.com/playlist/abc123") == "spotify"

    def test_youtube_full_url(self):
        assert detect_source("https://www.youtube.com/playlist?list=PLxx") == "youtube"

    def test_youtu_be_short_url(self):
        assert detect_source("https://youtu.be/dQw4w9WgXcQ") == "youtube"

    def test_music_youtube(self):
        assert detect_source("https://music.youtube.com/playlist?list=PLxx") == "youtube"

    def test_uppercase_host_is_case_insensitive(self):
        assert detect_source("https://OPEN.SPOTIFY.COM/playlist/abc") == "spotify"

    def test_unknown_host_raises_invalid_input(self):
        with pytest.raises(InvalidInputError):
            detect_source("https://soundcloud.com/user/sets/mix")

    def test_empty_string_raises_invalid_input(self):
        with pytest.raises(InvalidInputError):
            detect_source("")

    def test_garbage_string_raises_invalid_input(self):
        with pytest.raises(InvalidInputError):
            detect_source("not a url at all")
