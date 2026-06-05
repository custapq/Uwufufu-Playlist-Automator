import pytest

from src.exceptions import (
    AutomationError,
    ConfigError,
    ElementNotFoundError,
    GameCreationError,
    InvalidInputError,
    LoginError,
    NavigationError,
    SpotifyError,
    SpotifyPlaylistNotFoundError,
    SpotifyScrapingError,
    UwufufuError,
    VideoAddError,
    YouTubeError,
    YouTubeSearchError,
)


class TestHierarchy:
    def test_all_inherit_from_base(self):
        for exc in (
            SpotifyError, YouTubeError, AutomationError, ConfigError, InvalidInputError,
        ):
            assert issubclass(exc, UwufufuError)

    def test_spotify_subclasses(self):
        assert issubclass(SpotifyPlaylistNotFoundError, SpotifyError)
        assert issubclass(SpotifyScrapingError, SpotifyError)

    def test_youtube_subclasses(self):
        assert issubclass(YouTubeSearchError, YouTubeError)

    def test_automation_subclasses(self):
        for exc in (LoginError, NavigationError, GameCreationError,
                    ElementNotFoundError, VideoAddError):
            assert issubclass(exc, AutomationError)


class TestCatchability:
    def test_base_catches_all(self):
        with pytest.raises(UwufufuError):
            raise LoginError("bad password")

    def test_spotify_base_catches_subclass(self):
        with pytest.raises(SpotifyError):
            raise SpotifyPlaylistNotFoundError("private playlist")

    def test_specific_does_not_catch_sibling(self):
        with pytest.raises(LoginError):
            raise LoginError("x")
        # A NavigationError must not be catchable as LoginError
        try:
            raise NavigationError("x")
        except LoginError:
            pytest.fail("NavigationError should not be caught as LoginError")
        except NavigationError:
            pass

    def test_message_is_preserved(self):
        exc = LoginError("verify your password")
        assert str(exc) == "verify your password"
