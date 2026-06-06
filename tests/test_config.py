from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import (
    AppConfig,
    SelectorConfig,
    TimingConfig,
    load_api_credentials,
    load_config,
    load_credentials_from_env,
    load_env_credentials,
)
from src.exceptions import ConfigError
from src.models import ApiCredentials


class TestAppConfigDefaults:
    def test_default_urls(self):
        config = AppConfig()
        assert config.uwufufu_url == "https://uwufufu.com"
        assert config.login_url == "https://uwufufu.com/auth/login"

    def test_default_browser_settings(self):
        config = AppConfig()
        assert config.headless is False
        assert config.window_size == "1920,1080"

    def test_default_subconfigs(self):
        config = AppConfig()
        assert isinstance(config.timing, TimingConfig)
        assert isinstance(config.selectors, SelectorConfig)

    def test_output_paths(self):
        config = AppConfig(output_dir="output", output_filename="links")
        assert config.output_txt == Path("output") / "links.txt"
        assert config.output_json == Path("output") / "links.json"


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        missing = tmp_path / "does_not_exist.yaml"
        config = load_config(str(missing))
        assert config == AppConfig()

    def test_loads_top_level_values(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "headless: true\nwindow_size: '1280,720'\nmax_retries: 5\n",
            encoding="utf-8",
        )
        config = load_config(str(yaml_file))
        assert config.headless is True
        assert config.window_size == "1280,720"
        assert config.max_retries == 5

    def test_loads_nested_timing(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "timing:\n  after_login: 9.0\n  after_click: 0.1\n",
            encoding="utf-8",
        )
        config = load_config(str(yaml_file))
        assert config.timing.after_login == 9.0
        assert config.timing.after_click == 0.1
        # Untouched values keep their defaults
        assert config.timing.between_scroll == 1.5

    def test_loads_nested_selectors(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "selectors:\n  login_email: \"input#custom-email\"\n",
            encoding="utf-8",
        )
        config = load_config(str(yaml_file))
        assert config.selectors.login_email == "input#custom-email"

    def test_empty_file_returns_defaults(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("", encoding="utf-8")
        config = load_config(str(yaml_file))
        assert config == AppConfig()


class TestEnvLoading:
    """Task 5.4 — PLAYLIST_URL replaces SPOTIFY_PLAYLIST_URL."""

    def test_load_env_credentials_reads_playlist_url(self):
        env = {"PLAYLIST_URL": "https://open.spotify.com/playlist/abc"}
        with patch.dict("os.environ", env, clear=True):
            _email, _password, playlist_url = load_env_credentials()
        assert playlist_url == "https://open.spotify.com/playlist/abc"

    def test_load_credentials_from_env_exposes_playlist_url(self):
        env = {
            "UWUFUFU_EMAIL": "u@e.com",
            "UWUFUFU_PASSWORD": "pw",
            "PLAYLIST_URL": "https://www.youtube.com/playlist?list=PLx",
        }
        with patch.dict("os.environ", env, clear=True):
            result = load_credentials_from_env()
        assert result.playlist_url == "https://www.youtube.com/playlist?list=PLx"

    def test_playlist_url_none_when_absent(self):
        env = {"UWUFUFU_EMAIL": "u@e.com", "UWUFUFU_PASSWORD": "pw"}
        with patch.dict("os.environ", env, clear=True):
            result = load_credentials_from_env()
        assert result.playlist_url is None


class TestLoadApiCredentials:
    """Task 5.4 — Spotify + YouTube API key loading."""

    _FULL = {
        "SPOTIFY_CLIENT_ID": "cid",
        "SPOTIFY_CLIENT_SECRET": "csecret",
        "YOUTUBE_API_KEY": "ykey",
    }

    def test_all_present_returns_api_credentials(self):
        with patch.dict("os.environ", self._FULL, clear=True):
            creds = load_api_credentials()
        assert creds == ApiCredentials("cid", "csecret", "ykey")

    def test_missing_spotify_id_raises_config_error(self):
        env = {k: v for k, v in self._FULL.items() if k != "SPOTIFY_CLIENT_ID"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ConfigError, match="SPOTIFY_CLIENT_ID"):
                load_api_credentials()

    def test_missing_youtube_key_raises_config_error(self):
        env = {k: v for k, v in self._FULL.items() if k != "YOUTUBE_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ConfigError, match="YOUTUBE_API_KEY"):
                load_api_credentials()

    def test_lists_all_missing_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ConfigError) as exc_info:
                load_api_credentials()
        message = str(exc_info.value)
        assert "SPOTIFY_CLIENT_ID" in message
        assert "SPOTIFY_CLIENT_SECRET" in message
        assert "YOUTUBE_API_KEY" in message
