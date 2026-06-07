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
        use_env=False, spotify_only=False, resume=None,
        config=None, output=None, verbose=False,
        category_id=16, start_time=0, end_time=0, no_publish=False,
        spotify_login=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _api_creds():
    return ApiCredentials(
        spotify_client_id="id",
        spotify_client_secret="secret",
    )


class TestParser:
    def test_help_builds(self):
        parser = main._build_parser()
        assert parser.prog == "uwufufu-automator"

    def test_parses_flags(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--spotify-only", "-v"])
        assert ns.spotify_only is True
        assert ns.verbose is True

    def test_parses_playlist_url(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--playlist-url", "https://x/playlist/1"])
        assert ns.playlist_url == "https://x/playlist/1"

    def test_parses_category_id(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--category-id", "19"])
        assert ns.category_id == 19

    def test_parses_clip_times(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--start-time", "10", "--end-time", "60"])
        assert ns.start_time == 10
        assert ns.end_time == 60

    def test_parses_no_publish(self):
        parser = main._build_parser()
        ns = parser.parse_args(["--no-publish"])
        assert ns.no_publish is True

    def test_defaults(self):
        parser = main._build_parser()
        ns = parser.parse_args([])
        assert ns.category_id == 16
        assert ns.start_time == 0
        assert ns.end_time == 0
        assert ns.no_publish is False


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
        game = main._resolve_game_config(
            _args(title="T", description="D", category_id=19, start_time=5, end_time=30, no_publish=True)
        )
        assert game == GameConfig(title="T", description="D", category_id=19, start_time=5, end_time=30, publish=False)

    def test_defaults_category_and_publish(self):
        game = main._resolve_game_config(_args(title="T", description="D"))
        assert game.category_id == 16
        assert game.publish is True

    def test_prompts_when_missing(self):
        with patch("builtins.input", side_effect=["MyTitle", "MyDesc"]):
            game = main._resolve_game_config(_args())
        assert game == GameConfig(title="MyTitle", description="MyDesc")


class TestReportError:
    def test_returns_one(self):
        assert main._report_error("boom", ValueError("x")) == 1


class TestStepExtractLinks:
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


class TestStepUwufufu:
    def _link(self, url="https://youtu.be/x", added=False):
        return YoutubeLink(track=Track("T", "A"), url=url, added=added)

    def _game(self, **kw):
        defaults = dict(title="Q", description="D", category_id=16,
                        start_time=0, end_time=0, publish=True)
        defaults.update(kw)
        return GameConfig(**defaults)

    def _creds(self):
        return Credentials(email="a@b.com", password="pw")

    @patch("src.main.mark_video_added")
    @patch("src.main.UwufufuAPIClient")
    @patch("builtins.input", return_value="y")
    def test_calls_login_create_import_publish(self, _inp, mock_cls, _mark):
        mock_client = mock_cls.return_value
        mock_client.import_tracks.return_value = MagicMock(
            game_id=42, slug="quiz", added=1, skipped=0, failed=0
        )

        result = main._step_uwufufu(
            [self._link()], self._creds(), self._game(), AppConfig(), "out.json"
        )

        assert result == 0
        mock_client.login.assert_called_once_with("a@b.com", "pw")
        mock_client.import_tracks.assert_called_once()
        mock_client.publish_game.assert_called_once_with(42, category_id=16)

    @patch("src.main.UwufufuAPIClient")
    @patch("builtins.input", return_value="y")
    def test_no_publish_skips_publish_call(self, _inp, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.import_tracks.return_value = MagicMock(
            game_id=7, slug=None, added=1, skipped=0, failed=0
        )

        main._step_uwufufu(
            [self._link()], self._creds(), self._game(publish=False), AppConfig(), "out.json"
        )

        mock_client.publish_game.assert_not_called()

    @patch("builtins.input", return_value="n")
    def test_cancel_returns_zero(self, _inp):
        result = main._step_uwufufu(
            [self._link()], self._creds(), self._game(), AppConfig(), "out.json"
        )
        assert result == 0

    def test_no_valid_links_returns_one(self):
        bad = YoutubeLink(track=Track("T", "A"), url=None)
        result = main._step_uwufufu(
            [bad], self._creds(), self._game(), AppConfig(), "out.json"
        )
        assert result == 1

    @patch("builtins.input", return_value="y")
    def test_all_already_added_returns_zero(self, _inp):
        link = self._link(added=True)
        result = main._step_uwufufu(
            [link], self._creds(), self._game(), AppConfig(), "out.json"
        )
        assert result == 0

    @patch("src.main.mark_video_added")
    @patch("src.main.UwufufuAPIClient")
    @patch("builtins.input", return_value="y")
    def test_passes_category_and_clip_times(self, _inp, mock_cls, _mark):
        mock_client = mock_cls.return_value
        mock_client.import_tracks.return_value = MagicMock(
            game_id=1, slug=None, added=1, skipped=0, failed=0
        )
        game = self._game(category_id=19, start_time=5, end_time=30)

        main._step_uwufufu([self._link()], self._creds(), game, AppConfig(), "out.json")

        _, kwargs = mock_client.import_tracks.call_args
        assert kwargs["start_time"] == 5
        assert kwargs["end_time"] == 30
        assert kwargs["create"]["category_id"] == 19
        mock_client.publish_game.assert_called_once_with(1, category_id=19)


class TestMainExceptionHandling:
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
