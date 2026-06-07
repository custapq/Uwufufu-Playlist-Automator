from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# Main Config
# ─────────────────────────────────────────────

@dataclass
class AppConfig:
    """Main application configuration."""

    # --- Output ---
    output_dir: str = "output"
    output_filename: str = "spotify_to_youtube"

    # --- Reliability ---
    max_retries: int = 3

    @property
    def output_txt(self) -> Path:
        return Path(self.output_dir) / f"{self.output_filename}.txt"

    @property
    def output_json(self) -> Path:
        return Path(self.output_dir) / f"{self.output_filename}.json"


# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load AppConfig from a YAML file if it exists, otherwise return defaults."""
    path = Path(config_path or "config.yaml")

    if not path.exists():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Drop keys that existed in v3 but are no longer valid — silently ignore
    # them so old config files don't blow up on upgrade.
    for stale in ("timing", "selectors", "headless", "window_size", "webdriver_timeout",
                  "uwufufu_url", "login_url", "create_game_url"):
        data.pop(stale, None)

    return AppConfig(**data)


def load_env_credentials() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Load raw credential strings from .env / environment.

    Returns:
        (email, password, playlist_url) — any may be None.
    """
    load_dotenv()
    email = os.getenv("UWUFUFU_EMAIL")
    password = os.getenv("UWUFUFU_PASSWORD")
    playlist_url = os.getenv("PLAYLIST_URL")
    return email, password, playlist_url


def load_credentials_from_env() -> Optional["UserInputFromEnv"]:
    """Load UwuFufu credentials from .env and return a typed namespace.

    Returns None if email or password is missing.
    """
    from types import SimpleNamespace

    email, password, playlist_url = load_env_credentials()

    if not email or not password:
        return None

    return SimpleNamespace(
        email=email,
        password=password,
        playlist_url=playlist_url,
    )


def load_api_credentials() -> "ApiCredentials":
    """Load Spotify API credentials from the environment.

    YOUTUBE_API_KEY is no longer required (yt-dlp is used instead).

    Raises:
        ConfigError: If Spotify credentials are missing.
    """
    from src.models import ApiCredentials
    from src.exceptions import ConfigError

    load_dotenv()
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    missing = []
    if not spotify_client_id:
        missing.append("SPOTIFY_CLIENT_ID")
    if not spotify_client_secret:
        missing.append("SPOTIFY_CLIENT_SECRET")

    if missing:
        raise ConfigError(
            f"Missing required API credentials in .env: {', '.join(missing)}"
        )

    return ApiCredentials(
        spotify_client_id=spotify_client_id,
        spotify_client_secret=spotify_client_secret,
        spotify_redirect_uri=spotify_redirect_uri,
    )
