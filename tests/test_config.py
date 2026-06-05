"""tests/test_config.py — Unit tests for configuration loading."""

from pathlib import Path

from src.config import AppConfig, SelectorConfig, TimingConfig, load_config


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
