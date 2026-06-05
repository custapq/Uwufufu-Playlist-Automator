"""
main.py — Entry point for Uwufufu-Automator
"""

from __future__ import annotations

import getpass
import logging
import sys

from src.config import load_config, load_credentials_from_env
from src.exceptions import (
    AutomationError,
    GameCreationError,
    LoginError,
    NavigationError,
    SpotifyError,
    UwufufuError,
    YouTubeError,
)
from src.file_manager import load_youtube_links, save_youtube_links
from src.models import Credentials, GameConfig, UserInput
from src.spotify_scraper import SpotifyScraper
from src.utils.browser import managed_browser
from src.utils.logger import setup_logger
from src.uwufufu_automator import UwuFufuAutomator
from src.youtube_searcher import YouTubeSearcher

logger = logging.getLogger(__name__)


def _collect_user_input(config) -> UserInput:
    """Prompt the user for all required inputs, loading from .env where available."""
    env = load_credentials_from_env()

    print("\n=== Spotify Playlist ===")
    if env and env.spotify_url:
        spotify_url = env.spotify_url
        print(f"Loaded Spotify URL from .env: {spotify_url}")
    else:
        spotify_url = input("Enter your Spotify playlist URL: ")

    print("\n=== UwuFufu Credentials ===")
    if env:
        email = env.email
        password = env.password
        print(f"Loaded credentials from .env (email: {email})")
    else:
        email = input("Enter your UwuFufu email: ")
        password = getpass.getpass("Enter your UwuFufu password: ")

    print("\n=== UwuFufu Game Details ===")
    title = input("Enter your game title: ")
    description = input("Enter your game description: ")

    return UserInput(
        spotify_url=spotify_url,
        credentials=Credentials(email=email, password=password),
        game=GameConfig(title=title, description=description),
    )


def main() -> int:
    """Run the full Spotify → YouTube → UwuFufu automation pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    setup_logger()
    config = load_config()

    print("=" * 50)
    print("🎵 Spotify to UwuFufu Automation Tool 🎮")
    print("=" * 50)

    user_input = _collect_user_input(config)

    # ── Step 1: Scrape Spotify ──────────────────────────────────────────
    try:
        with managed_browser(headless=config.headless) as (driver, _):
            scraper = SpotifyScraper(driver, config)
            tracks = scraper.get_tracks(user_input.spotify_url)
    except SpotifyError as exc:
        logger.error("❌ Failed to extract Spotify tracks: %s", exc)
        return 1

    logger.info("✅ Extracted %d tracks", len(tracks))

    # ── Step 2: Search YouTube ──────────────────────────────────────────
    try:
        searcher = YouTubeSearcher(config)
        youtube_links = searcher.search_all(tracks)
    except YouTubeError as exc:
        logger.error("❌ YouTube search failed: %s", exc)
        return 1

    save_youtube_links(youtube_links, config.output_dir, config.output_filename)

    valid_links = [link for link in youtube_links if link.is_valid]
    if not valid_links:
        logger.error("❌ No valid YouTube links found — cannot continue")
        return 1

    logger.info("Found %d/%d valid YouTube links", len(valid_links), len(tracks))

    # ── Step 3: UwuFufu automation ──────────────────────────────────────
    proceed = input("\nReady to proceed with UwuFufu automation? (y/n): ").lower()
    if proceed != "y":
        print("Automation cancelled. YouTube links saved to output/")
        return 0

    try:
        with managed_browser(headless=config.headless) as (driver, _):
            automator = UwuFufuAutomator(driver, config)
            automator.login(user_input.credentials)
            automator.navigate_to_create_game()
            automator.fill_game_details(user_input.game)
            automator.open_choices_panel()
            automator.reveal_video_input()
            success, total = automator.add_all_videos(valid_links)
            logger.info("🎉 Added %d/%d videos to UwuFufu", success, total)
            input("\nPress Enter to close the browser...")
    except LoginError as exc:
        logger.error("❌ Login failed: %s", exc)
        return 1
    except (NavigationError, GameCreationError) as exc:
        logger.error("❌ Game creation failed: %s", exc)
        return 1
    except AutomationError as exc:
        logger.error("❌ Automation error: %s", exc)
        return 1
    except UwufufuError as exc:
        logger.error("❌ Unexpected error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
