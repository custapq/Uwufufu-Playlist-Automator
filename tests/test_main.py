"""tests/test_main.py — Unit tests for main.py argument resolution and helpers."""

import argparse
from types import SimpleNamespace
from unittest.mock import patch

from src import main
from src.models import Credentials, GameConfig


def _args(**overrides):
    defaults = dict(
        spotify_url=None, email=None, title=None, description=None,
        use_env=False, spotify_only=False, resume=None, headless=False,
        config=None, output=None, verbose=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


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


class TestResolveCredentials:
    def test_spotify_only_skips_credentials(self):
        assert main._resolve_credentials(_args(spotify_only=True)) is None

    def test_uses_email_arg_and_prompts_password(self):
        with patch("getpass.getpass", return_value="secret"):
            creds = main._resolve_credentials(_args(email="a@b.com"))
        assert creds == Credentials(email="a@b.com", password="secret")

    def test_loads_from_env(self):
        env = SimpleNamespace(email="env@b.com", password="envpw", spotify_url=None)
        with patch("src.main.load_credentials_from_env", return_value=env):
            creds = main._resolve_credentials(_args(use_env=True))
        assert creds == Credentials(email="env@b.com", password="envpw")


class TestResolveSpotifyUrl:
    def test_uses_arg(self):
        url = main._resolve_spotify_url(_args(spotify_url="https://x/playlist/1"))
        assert url == "https://x/playlist/1"

    def test_falls_back_to_prompt(self):
        with patch("builtins.input", return_value="https://prompted/playlist"):
            url = main._resolve_spotify_url(_args())
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
