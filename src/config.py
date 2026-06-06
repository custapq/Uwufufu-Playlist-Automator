from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# Sub-configs
# ─────────────────────────────────────────────

@dataclass
class TimingConfig:
    """
    All delay values used throughout the automation (in seconds).

    Replaces magic numbers scattered across auto_uwu.py, e.g.:
      time.sleep(3)   → time.sleep(timing.after_page_submit)
      time.sleep(0.3) → time.sleep(timing.after_click)
    """

    after_login: float = 2.0
    """Wait for redirect after a successful login."""

    after_click: float = 0.3
    """Wait for DOM to update after a click."""

    after_page_submit: float = 3.0
    """Wait for server response after form submission."""

    spotify_initial_load: float = 3.0
    """Wait for Spotify to finish rendering after page load."""

    between_scroll: float = 1.5
    """Wait between scroll steps while loading all tracks."""

    youtube_search_min: float = 1.0
    """Minimum delay between YouTube searches (rate-limit protection)."""

    youtube_search_max: float = 2.5
    """Maximum delay between YouTube searches (rate-limit protection)."""

    between_video_add: float = 0.5
    """Wait after each video is added to the UwuFufu game."""

    reveal_video_input: float = 2.0
    """Wait for the video input field to appear after clicking the icon."""

    choices_panel: float = 2.0
    """Wait for the Choices panel to open."""

    page_settle: float = 1.0
    """Wait for a page or form section to render after navigation."""

    after_input: float = 0.2
    """Wait after clearing or typing into a form field."""

    after_scroll: float = 0.8
    """Wait after scrolling an element into view before interacting with it."""

    short_pause: float = 0.5
    """Generic short settle delay between UI interactions."""


@dataclass
class SelectorConfig:
    """
    CSS selectors and XPath expressions for UwuFufu and Spotify.

    Centralised here so that when the UI changes, only this file needs updating.
    Replaces the global constants in the original auto_uwu.py.
    """

    # --- UwuFufu Login ---
    login_email: str = "input[name='email']"
    login_password: str = "input[name='password']"
    login_button: str = "button[type='submit']"

    # --- UwuFufu Navigation ---
    create_game_link: str = "a[href='/create-game']"

    # --- UwuFufu Game Form ---
    title_input: str = "input#title"
    description_input: str = "textarea#description"
    choices_button: str = "button[type='submit'].bg-uwu-red.py-2.px-4"
    choices_xpath: str = "//span[normalize-space()='Choices']"

    # --- UwuFufu Video Input ---
    video_icon: str = "svg.lucide-tv-minimal-play"
    youtube_url_input_id: str = "youtubeUrl"
    add_video_button: str = "button.bg-uwu-red[type='submit']"

    # --- Spotify ---
    tracklist_row: str = "[data-testid='tracklist-row']"
    track_link: str = "[data-testid='internal-track-link']"
    artist_link: str = "a[data-testid='artist-link']"
    artists_container: str = "span[data-testid='artists-container']"


# ─────────────────────────────────────────────
# Main Config
# ─────────────────────────────────────────────

@dataclass
class AppConfig:
    """Main application configuration — replaces global constants in auto_uwu.py."""

    # --- URLs ---
    uwufufu_url: str = "https://uwufufu.com"
    login_url: str = "https://uwufufu.com/auth/login"
    create_game_url: str = "https://uwufufu.com/create-game"

    # --- Output ---
    output_dir: str = "output"
    output_filename: str = "spotify_to_youtube"

    # --- Browser ---
    headless: bool = False
    window_size: str = "1920,1080"

    # --- Reliability ---
    webdriver_timeout: int = 30
    """Seconds — WebDriverWait timeout."""

    max_retries: int = 3
    """Number of retry attempts on failure."""

    # --- Sub-configs ---
    timing: TimingConfig = field(default_factory=TimingConfig)
    selectors: SelectorConfig = field(default_factory=SelectorConfig)

    @property
    def output_txt(self) -> Path:
        """Path to the human-readable output text file."""
        return Path(self.output_dir) / f"{self.output_filename}.txt"

    @property
    def output_json(self) -> Path:
        """Path to the machine-readable JSON file (used for resume support)."""
        return Path(self.output_dir) / f"{self.output_filename}.json"


# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load AppConfig from a YAML file if it exists, otherwise return defaults.

    Args:
        config_path: Path to config.yaml (default: "config.yaml").

    Returns:
        A fully initialised AppConfig instance.
    """
    path = Path(config_path or "config.yaml")

    if not path.exists():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    timing_data = data.pop("timing", {})
    selectors_data = data.pop("selectors", {})

    timing = TimingConfig(**timing_data) if timing_data else TimingConfig()
    selectors = SelectorConfig(**selectors_data) if selectors_data else SelectorConfig()

    return AppConfig(timing=timing, selectors=selectors, **data)


def load_env_credentials() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load raw credential strings from a .env file or environment variables.

    Returns:
        A tuple of (email, password, spotify_url).
        Each value is None if not found in the environment.
    """
    load_dotenv()
    email = os.getenv("UWUFUFU_EMAIL")
    password = os.getenv("UWUFUFU_PASSWORD")
    playlist_url = os.getenv("PLAYLIST_URL")
    return email, password, playlist_url


def load_credentials_from_env() -> Optional["UserInputFromEnv"]:
    """
    Load credentials from a .env file and return typed model objects.

    Returns a named tuple-like structure when all required fields are present,
    or None if email or password is missing from the environment.

    This is the preferred function for callers that want model objects
    rather than raw strings. get_user_credentials() uses this internally.

    Returns:
        A namespace with .email, .password, and optionally .spotify_url,
        or None if required credentials are not set.
    """
    from types import SimpleNamespace

    email, password, playlist_url = load_env_credentials()

    if not email or not password:
        return None

    return SimpleNamespace(
        email=email,
        password=password,
        playlist_url=playlist_url,  # may be None — caller can prompt if needed
    )


def load_api_credentials() -> "ApiCredentials":
    """
    Load Spotify and YouTube API credentials from the environment.

    Raises:
        ConfigError: If any required API credentials are missing.
    """
    from src.models import ApiCredentials
    from src.exceptions import ConfigError

    load_dotenv()
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")

    missing = []
    if not spotify_client_id: missing.append("SPOTIFY_CLIENT_ID")
    if not spotify_client_secret: missing.append("SPOTIFY_CLIENT_SECRET")
    if not youtube_api_key: missing.append("YOUTUBE_API_KEY")

    if missing:
        raise ConfigError(
            f"Missing required API credentials in .env: {', '.join(missing)}"
        )

    return ApiCredentials(
        spotify_client_id=spotify_client_id,
        spotify_client_secret=spotify_client_secret,
        youtube_api_key=youtube_api_key,
    )
