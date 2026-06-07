from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import (
    AppConfig,
    load_api_credentials,
    load_config,
    load_credentials_from_env,
    load_env_credentials,
)
from src.exceptions import ConfigError
from src.models import ApiCredentials


class TestAppConfigDefaults:
    def test_output_paths(self):
        config = AppConfig(output_dir="output", output_filename="links")
        assert config.output_txt == Path("output") / "links.txt"
        assert config.output_json == Path("output") / "links.json"

    def test_default_max_retries(self):
        config = AppConfig()
        assert config.max_retries == 3


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        missing = tmp_path / "does_not_exist.yaml"
        config = load_config(str(missing))
        assert config == AppConfig()

    def test_loads_max_retries(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("max_retries: 5\n", encoding="utf-8")
        config = load_config(str(yaml_file))
        assert config.max_retries == 5

    def test_stale_v3_keys_are_ignored(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "headless: true\nwindow_size: '1280,720'\nwebdriver_timeout: 60\n"
            "timing:\n  after_login: 9.0\nselectors:\n  login_email: 'x'\n",
            encoding="utf-8",
        )
        config = load_config(str(yaml_file))
        assert config == AppConfig()

    def test_empty_file_returns_defaults(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("", encoding="utf-8")
        config = load_config(str(yaml_file))
        assert config == AppConfig()


class TestEnvLoading:
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
    _FULL = {
        "SPOTIFY_CLIENT_ID": "cid",
        "SPOTIFY_CLIENT_SECRET": "csecret",
    }

    def test_all_present_returns_api_credentials(self):
        with patch.dict("os.environ", self._FULL, clear=True):
            creds = load_api_credentials()
        assert creds == ApiCredentials("cid", "csecret")

    def test_missing_spotify_id_raises_config_error(self):
        env = {k: v for k, v in self._FULL.items() if k != "SPOTIFY_CLIENT_ID"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ConfigError, match="SPOTIFY_CLIENT_ID"):
                load_api_credentials()

    def test_missing_spotify_secret_raises_config_error(self):
        env = {k: v for k, v in self._FULL.items() if k != "SPOTIFY_CLIENT_SECRET"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ConfigError, match="SPOTIFY_CLIENT_SECRET"):
                load_api_credentials()

    def test_lists_all_missing_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ConfigError) as exc_info:
                load_api_credentials()
        message = str(exc_info.value)
        assert "SPOTIFY_CLIENT_ID" in message
        assert "SPOTIFY_CLIENT_SECRET" in message

    def test_youtube_api_key_not_required(self):
        # YOUTUBE_API_KEY is no longer required (yt-dlp is used instead)
        with patch.dict("os.environ", self._FULL, clear=True):
            creds = load_api_credentials()
        assert not hasattr(creds, "youtube_api_key")
