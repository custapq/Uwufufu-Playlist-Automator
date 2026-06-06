import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src import main
from src.config import AppConfig
from src.exceptions import InvalidInputError, SpotifyError, YouTubePlaylistError
from src.models import ApiCredentials, Credentials, GameConfig, Track, YoutubeLink


def _args(**overrides):
    defaults = dict(
        playlist_url=None, email=None, title=None, description=None,
        use_env=False, spotify_only=False, resume=None, headless=False,
        keep_browser_open=False, config=None, output=None, verbose=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _api_creds():
    return ApiCredentials(
        spotify_client_id="id",
        spotify_client_secret="secret",
        youtube_api_key="yt_key",
    )


class TestParser:
    def test_help_builds(self):
        parser = main._build_parser()
        assert parser.prog == "uwufufu-automator"

    def test_parses_flags(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--headless", "--spotify-only", "-v"])
        assert ns.headless is True
        assert ns.spotify_only is True
        assert ns.verbose is True

    def test_parses_playlist_url(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--playlist-url", "https://x/playlist/1"])
        assert ns.playlist_url == "https://x/playlist/1"


class TestResolveCredentials:
    def test_spotify_only_skips_credentials(self):
        assert main._resolve_credentials(_args(spotify_only=True)) is None

    def test_uses_email_arg_and_prompts_password(self):
        with patch("getpass.getpass", return_value="secret"):
            creds = main._resolve_credentials(_args(email="a@b.com"))
        assert creds == Credentials(email="a@b.com", password="secret")

    def test_loads_from_env(self):
        env = SimpleNamespace(email="env@b.com", password="envpw", playlist_url=None)
        with patch("src.main.load_credentials_from_env", return_value=env):
            creds = main._resolve_credentials(_args(use_env=True))
        assert creds == Credentials(email="env@b.com", password="envpw")


class TestResolvePlaylistUrl:
    def test_uses_arg(self):
        url = main._resolve_playlist_url(_args(playlist_url="https://x/playlist/1"))
        assert url == "https://x/playlist/1"

    def test_loads_from_env(self):
        env = SimpleNamespace(
            email="e", password="p", playlist_url="https://open.spotify.com/playlist/abc"
        )
        with patch("src.main.load_credentials_from_env", return_value=env):
            url = main._resolve_playlist_url(_args(use_env=True))
        assert url == "https://open.spotify.com/playlist/abc"

    def test_falls_back_to_prompt(self):
        with patch("builtins.input", return_value="https://prompted/playlist"):
            url = main._resolve_playlist_url(_args())
        assert url == "https://prompted/playlist"


class TestResolveGameConfig:
    def test_uses_args(self):
        game = main._resolve_game_config(_args(title="T", description="D"))
        assert game == GameConfig(title="T", description="D")

    def test_prompts_when_missing(self):
        with patch("builtins.input", side_effect=["MyTitle", "MyDesc"]):
            game = main._resolve_game_config(_args())
        assert game == GameConfig(title="MyTitle", description="MyDesc")


class TestReportError:
    def test_returns_one(self):
        assert main._report_error("boom", ValueError("x")) == 1


class TestStepExtractLinks:
    """Task 5.2 — routing by detected source (requirement 3 integration)."""

    @patch("src.main.save_youtube_links")
    @patch("src.main.YouTubeAPI")
    @patch("src.main.SpotifyTokenManager")
    @patch("src.main.SpotifyAPI")
    @patch("src.main.detect_source", return_value="spotify")
    def test_spotify_source_uses_get_tracks_then_search(
        self, _detect, mock_spotify_cls, _token, mock_youtube_cls, _save
    ):
        mock_spotify_cls.return_value.get_tracks.return_value = [Track("A", "1")]
        mock_youtube_cls.return_value.search_all.return_value = [
            YoutubeLink(track=Track("A", "1"), url="https://youtu.be/x")
        ]

        result = main._step_extract_links("https://open.spotify.com/playlist/x",
                                          AppConfig(), _api_creds())

        mock_spotify_cls.return_value.get_tracks.assert_called_once()
        mock_youtube_cls.return_value.search_all.assert_called_once()
        mock_youtube_cls.return_value.get_playlist_tracks.assert_not_called()
        assert len(result) == 1

    @patch("src.main.save_youtube_links")
    @patch("src.main.YouTubeAPI")
    @patch("src.main.SpotifyAPI")
    @patch("src.main.detect_source", return_value="youtube")
    def test_youtube_source_uses_get_playlist_tracks(
        self, _detect, mock_spotify_cls, mock_youtube_cls, _save
    ):
        mock_youtube_cls.return_value.get_playlist_tracks.return_value = [
            YoutubeLink(track=Track("V", "Chan"), url="https://youtu.be/v")
        ]

        result = main._step_extract_links("https://www.youtube.com/playlist?list=PLx",
                                          AppConfig(), _api_creds())

        mock_youtube_cls.return_value.get_playlist_tracks.assert_called_once()
        mock_spotify_cls.return_value.get_tracks.assert_not_called()
        mock_youtube_cls.return_value.search_all.assert_not_called()
        assert len(result) == 1

    @patch("src.main.save_youtube_links")
    @patch("src.main.YouTubeAPI")
    @patch("src.main.SpotifyTokenManager")
    @patch("src.main.SpotifyAPI")
    @patch("src.main.detect_source", return_value="spotify")
    def test_saves_links_with_config_paths(
        self, _detect, mock_spotify_cls, _token, mock_youtube_cls, mock_save
    ):
        mock_spotify_cls.return_value.get_tracks.return_value = [Track("A", "1")]
        links = [YoutubeLink(track=Track("A", "1"), url="https://youtu.be/x")]
        mock_youtube_cls.return_value.search_all.return_value = links
        config = AppConfig(output_dir="myout", output_filename="myfile")

        main._step_extract_links("https://open.spotify.com/playlist/x", config, _api_creds())

        mock_save.assert_called_once_with(links, "myout", "myfile")

    @patch("src.main.detect_source", side_effect=InvalidInputError("bad url"))
    def test_invalid_source_propagates_invalid_input(self, _detect):
        with pytest.raises(InvalidInputError):
            main._step_extract_links("ftp://nope", AppConfig(), _api_creds())


class TestMainExceptionHandling:
    """Task 5.3 — main() maps domain errors to exit code 1."""

    def _run_with_extract_error(self, exc):
        argv = ["--playlist-url", "https://open.spotify.com/playlist/x", "--spotify-only"]
        with patch("src.main.load_api_credentials", return_value=_api_creds()), \
             patch("src.main._step_extract_links", side_effect=exc):
            return main.main(argv)

    def test_invalid_input_error_returns_1(self):
        assert self._run_with_extract_error(InvalidInputError("bad")) == 1

    def test_youtube_playlist_error_returns_1(self):
        assert self._run_with_extract_error(YouTubePlaylistError("private")) == 1

    def test_spotify_error_returns_1(self):
        assert self._run_with_extract_error(SpotifyError("boom")) == 1
