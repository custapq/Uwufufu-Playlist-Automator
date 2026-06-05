"""
main.py — Entry point for Uwufufu-Automator
"""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from pathlib import Path
from typing import Optional

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


# ─────────────────────────────────────────────
# CLI argument parser
# ─────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uwufufu-automator",
        description="Spotify to UwuFufu Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # fully interactive
  python -m src.main

  # one-liner
  python -m src.main --spotify-url "https://open.spotify.com/playlist/..." \\
                     --email user@example.com --title "My Quiz" --description "Best songs"

  # load credentials from .env
  python -m src.main --use-env --title "My Quiz" --description "Best songs"

  # headless browser (no visible window)
  python -m src.main --headless

  # extract Spotify + YouTube links only (skip UwuFufu)
  python -m src.main --spotify-only --spotify-url "https://open.spotify.com/playlist/..."

  # resume UwuFufu step from a saved JSON file
  python -m src.main --resume output/spotify_to_youtube.json \\
                     --email user@example.com --title "My Quiz" --description "Best songs"

  # verbose / debug logging
  python -m src.main -v
        """,
    )

    # ── Input ───────────────────────────────────────────────────────────
    parser.add_argument("--spotify-url", metavar="URL", help="Spotify playlist URL")
    parser.add_argument("--email", metavar="EMAIL", help="UwuFufu account email")
    parser.add_argument("--title", metavar="TEXT", help="Game title")
    parser.add_argument("--description", metavar="TEXT", help="Game description")

    # ── Credentials source ──────────────────────────────────────────────
    parser.add_argument(
        "--use-env",
        action="store_true",
        help="Load credentials from .env file instead of prompting",
    )

    # ── Run modes ───────────────────────────────────────────────────────
    parser.add_argument(
        "--spotify-only",
        action="store_true",
        help="Only scrape Spotify and find YouTube links — skip UwuFufu automation",
    )
    parser.add_argument(
        "--resume",
        metavar="FILE",
        help="Skip Spotify + YouTube steps; load links from this JSON file",
    )

    # ── Browser ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without a visible window",
    )

    # ── Config / output ─────────────────────────────────────────────────
    parser.add_argument("--config", metavar="FILE", help="Path to config.yaml")
    parser.add_argument("--output", metavar="FILE", help="Output base path (without extension)")

    # ── Logging ─────────────────────────────────────────────────────────
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    return parser


# ─────────────────────────────────────────────
# Credential / input resolution
# ─────────────────────────────────────────────

def _resolve_credentials(args: argparse.Namespace) -> Optional[Credentials]:
    """Return Credentials from args / .env / interactive prompt, or None if not needed."""
    if args.spotify_only:
        return None

    env = load_credentials_from_env() if args.use_env else None

    email = args.email or (env.email if env else None)
    password = env.password if (env and not args.email) else None

    if not email:
        email = input("Enter your UwuFufu email: ")
    if not password:
        password = getpass.getpass("Enter your UwuFufu password: ")

    return Credentials(email=email, password=password)


def _resolve_spotify_url(args: argparse.Namespace) -> str:
    if args.spotify_url:
        return args.spotify_url

    env = load_credentials_from_env() if args.use_env else None
    if env and env.spotify_url:
        print(f"Loaded Spotify URL from .env: {env.spotify_url}")
        return env.spotify_url

    return input("Enter your Spotify playlist URL: ")


def _resolve_game_config(args: argparse.Namespace) -> GameConfig:
    title = args.title or input("Enter your game title: ")
    description = args.description or input("Enter your game description: ")
    return GameConfig(title=title, description=description)


# ─────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────

def _step_spotify_and_youtube(spotify_url: str, config):
    """Scrape Spotify then search YouTube; return list of YoutubeLink."""
    with managed_browser(headless=config.headless) as (driver, _):
        scraper = SpotifyScraper(driver, config)
        tracks = scraper.get_tracks(spotify_url)

    logger.info("✅ Extracted %d tracks", len(tracks))

    searcher = YouTubeSearcher(config)
    youtube_links = searcher.search_all(tracks)

    output_dir = config.output_dir
    output_filename = config.output_filename
    save_youtube_links(youtube_links, output_dir, output_filename)

    return youtube_links


def _step_uwufufu(youtube_links, credentials: Credentials, game: GameConfig, config):
    """Run the UwuFufu automation step."""
    valid_links = [link for link in youtube_links if link.is_valid]
    if not valid_links:
        logger.error("❌ No valid YouTube links found — cannot continue")
        return 1

    logger.info("Found %d/%d valid YouTube links", len(valid_links), len(youtube_links))

    proceed = input("\nReady to proceed with UwuFufu automation? (y/n): ").lower()
    if proceed != "y":
        print("Automation cancelled. YouTube links saved to output/")
        return 0

    with managed_browser(headless=config.headless) as (driver, _):
        automator = UwuFufuAutomator(driver, config)
        automator.login(credentials)
        automator.navigate_to_create_game()
        automator.fill_game_details(game)
        automator.open_choices_panel()
        automator.reveal_video_input()
        success, total = automator.add_all_videos(valid_links)
        logger.info("🎉 Added %d/%d videos to UwuFufu", success, total)
        input("\nPress Enter to close the browser...")

    return 0


# ─────────────────────────────────────────────
# main()
# ─────────────────────────────────────────────

def main(argv=None) -> int:
    """Run the automation pipeline according to CLI arguments.

    Returns:
        0 on success, 1 on failure.
    """
    args = _build_parser().parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)

    config = load_config(args.config)

    # Override config with CLI flags
    if args.headless:
        config.headless = True
    if args.output:
        p = Path(args.output)
        config.output_dir = str(p.parent)
        config.output_filename = p.stem

    print("=" * 50)
    print("🎵 Spotify to UwuFufu Automation Tool 🎮")
    print("=" * 50)

    try:
        # ── --resume mode: skip Spotify + YouTube ──────────────────────
        if args.resume:
            logger.info("Resuming from: %s", args.resume)
            youtube_links = load_youtube_links(args.resume)
            credentials = _resolve_credentials(args)
            game = _resolve_game_config(args)
            return _step_uwufufu(youtube_links, credentials, game, config)

        # ── --spotify-only mode ────────────────────────────────────────
        spotify_url = _resolve_spotify_url(args)

        youtube_links = _step_spotify_and_youtube(spotify_url, config)

        if args.spotify_only:
            valid = sum(1 for l in youtube_links if l.is_valid)
            logger.info("Spotify-only mode complete. %d/%d links found.", valid, len(youtube_links))
            return 0

        # ── Full pipeline ──────────────────────────────────────────────
        credentials = _resolve_credentials(args)
        game = _resolve_game_config(args)
        return _step_uwufufu(youtube_links, credentials, game, config)

    except SpotifyError as exc:
        logger.error("❌ Spotify error: %s", exc)
        return 1
    except YouTubeError as exc:
        logger.error("❌ YouTube error: %s", exc)
        return 1
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


if __name__ == "__main__":
    sys.exit(main())
