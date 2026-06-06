from __future__ import annotations

import argparse
import getpass
import logging
import sys
from pathlib import Path
from typing import Optional

from src.config import AppConfig, load_config, load_credentials_from_env, load_api_credentials
from src.exceptions import (
    AutomationError,
    GameCreationError,
    InvalidInputError,
    LoginError,
    NavigationError,
    SpotifyError,
    UwufufuError,
    YouTubeError,
    YouTubePlaylistError,
)
from src.utils.playlist import detect_source
from src.file_manager import load_youtube_links, mark_video_added, save_youtube_links
from src.models import Credentials, GameConfig, UserInput, YoutubeLink, ApiCredentials
from src.spotify_api import SpotifyAPI
from src.utils.browser import managed_browser
from src.utils.logger import setup_logger
from src.utils.spotify_auth import SpotifyTokenManager  # noqa: F401 (kept for --resume compat)
from src.utils.spotify_oauth import SpotifyUserAuth
from src.uwufufu_automator import UwuFufuAutomator
from src.youtube_api import YouTubeAPI

logger = logging.getLogger(__name__)


def _report_error(message: str, exc: Exception) -> int:
    """Log an actionable error message (console + file) plus a full traceback (file only).

    The console handler runs at INFO level, so the DEBUG traceback is written
    only to the log file — keeping the console clean while preserving detail.

    Returns:
        1, so callers can `return _report_error(...)`.
    """
    logger.error("❌ %s: %s", message, exc)
    logger.debug("Full traceback for the error above:", exc_info=True)
    return 1


# ─────────────────────────────────────────────
# CLI argument parser
# ─────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uwufufu-automator",
        description="Playlist to UwuFufu Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # fully interactive
  python -m src.main

  # one-liner (Spotify or YouTube playlist)
  python -m src.main --playlist-url "https://open.spotify.com/playlist/..." \\
                     --email user@example.com --title "My Quiz" --description "Best songs"

  # load credentials from .env
  python -m src.main --use-env --title "My Quiz" --description "Best songs"

  # headless browser (no visible window)
  python -m src.main --headless

  # extract playlist + YouTube links only (skip UwuFufu)
  python -m src.main --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

  # Spotify OAuth: log in via browser to read your OWN playlist (first time)
  python -m src.main --spotify-login --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

  # Spotify OAuth: subsequent runs reuse the cached token (no --spotify-login needed)
  python -m src.main --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

  # resume UwuFufu step from a saved JSON file
  python -m src.main --resume output/spotify_to_youtube.json \\
                     --email user@example.com --title "My Quiz" --description "Best songs"

  # verbose / debug logging
  python -m src.main -v
        """,
    )

    # ── Input ───────────────────────────────────────────────────────────
    parser.add_argument("--playlist-url", metavar="URL", help="Spotify or YouTube playlist URL")
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
        help="Only fetch playlist and find YouTube links — skip UwuFufu automation",
    )
    parser.add_argument(
        "--resume",
        metavar="FILE",
        help="Skip Spotify + YouTube steps; load links from this JSON file",
    )
    parser.add_argument(
        "--spotify-login",
        action="store_true",
        help=(
            "Force a fresh Spotify browser login (Authorization Code flow). "
            "Use this the first time, or to switch accounts. "
            "After the first login the refresh token is cached and subsequent "
            "runs do not need this flag."
        ),
    )

    # ── Browser ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without a visible window",
    )
    parser.add_argument(
        "--keep-browser-open",
        action="store_true",
        help="On error, leave the browser open and pause (for debugging)",
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


def _resolve_playlist_url(args: argparse.Namespace) -> str:
    if args.playlist_url:
        return args.playlist_url

    env = load_credentials_from_env() if args.use_env else None
    if env and env.playlist_url:
        print(f"Loaded playlist URL from .env: {env.playlist_url}")
        return env.playlist_url

    return input("Enter your Spotify or YouTube playlist URL: ")


def _resolve_game_config(args: argparse.Namespace) -> GameConfig:
    title = args.title or input("Enter your game title: ")
    description = args.description or input("Enter your game description: ")
    return GameConfig(title=title, description=description)


# ─────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────

def _step_extract_links(
    playlist_url: str,
    config: AppConfig,
    api_creds: ApiCredentials,
    keep_open: bool = False,
    spotify_login: bool = False,
) -> list[YoutubeLink]:
    """Fetch tracks from a Spotify or YouTube playlist; return list of YoutubeLink.

    For Spotify sources, ``SpotifyUserAuth`` (Authorization Code flow) is always
    used because Client Credentials cannot read playlist tracks after Spotify's
    February 2026 API change.  The refresh token is cached on disk so the
    interactive browser login only fires on the first run (or when
    ``spotify_login=True`` is passed to force a fresh login).
    """
    source = detect_source(playlist_url)

    if source == "spotify":
        auth = SpotifyUserAuth(api_creds)
        if spotify_login:
            logger.info("--spotify-login: starting fresh Spotify browser login…")
            auth.login(force=True)
        spotify_api = SpotifyAPI(auth)
        tracks = spotify_api.get_tracks(playlist_url)
        logger.info("Extracted %d tracks from Spotify playlist", len(tracks))
        youtube_api = YouTubeAPI()
        youtube_links = youtube_api.search_all(tracks)

    elif source == "youtube":
        youtube_api = YouTubeAPI()
        youtube_links = youtube_api.get_playlist_tracks(playlist_url)
        logger.info("Extracted %d videos from YouTube playlist", len(youtube_links))

    else:
        raise InvalidInputError(f"Unknown playlist source: {source}")

    save_youtube_links(youtube_links, config.output_dir, config.output_filename)
    return youtube_links


def _step_uwufufu(
    youtube_links: list[YoutubeLink],
    credentials: Credentials,
    game: GameConfig,
    config: AppConfig,
    json_path: str,
    keep_open: bool = False,
) -> int:
    """Run the UwuFufu automation step.

    Skips links already marked added_to_uwufufu (resume) and persists progress
    to ``json_path`` after each successful video add.
    """
    valid_links = [link for link in youtube_links if link.is_valid]
    if not valid_links:
        logger.error("❌ No valid YouTube links found — cannot continue")
        return 1

    pending = [link for link in valid_links if not link.added]
    already_added = len(valid_links) - len(pending)

    if already_added:
        logger.info("Resuming — %d videos already added, %d remaining",
                    already_added, len(pending))
    else:
        logger.info("Found %d/%d valid YouTube links", len(valid_links), len(youtube_links))

    if not pending:
        logger.info("🎉 All videos were already added — nothing to do")
        return 0

    proceed = input("\nReady to proceed with UwuFufu automation? (y/n): ").lower()
    if proceed != "y":
        print("Automation cancelled. YouTube links saved to output/")
        return 0

    def _persist(link: YoutubeLink) -> None:
        mark_video_added(json_path, link.track.name, link.track.artist)

    with managed_browser(
        headless=config.headless, keep_open_on_error=keep_open
    ) as (driver, _):
        automator = UwuFufuAutomator(driver, config)
        automator.login(credentials)
        automator.navigate_to_create_game()
        automator.fill_game_details(game)
        automator.open_choices_panel()
        automator.reveal_video_input()
        success, total = automator.add_all_videos(pending, on_added=_persist)
        logger.info("🎉 Added %d/%d videos to UwuFufu", success, total)
        input("\nPress Enter to close the browser...")

    return 0


# ─────────────────────────────────────────────
# main()
# ─────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> int:
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
    try:
        print("🎵 Playlist to UwuFufu Automation Tool 🎮")
    except UnicodeEncodeError:
        print("Playlist to UwuFufu Automation Tool")
    print("=" * 50)

    try:
        # ── --resume mode: skip Spotify + YouTube ──────────────────────
        if args.resume:
            logger.info("Resuming from: %s", args.resume)
            youtube_links = load_youtube_links(args.resume)
            credentials = _resolve_credentials(args)
            game = _resolve_game_config(args)
            return _step_uwufufu(
                youtube_links, credentials, game, config, args.resume,
                keep_open=args.keep_browser_open,
            )

        # ── Fetch playlist + YouTube links ─────────────────────────────
        playlist_url = _resolve_playlist_url(args)
        api_creds = load_api_credentials()

        youtube_links = _step_extract_links(
            playlist_url,
            config,
            api_creds,
            keep_open=args.keep_browser_open,
            spotify_login=args.spotify_login,
        )

        if args.spotify_only:
            valid = sum(1 for l in youtube_links if l.is_valid)
            logger.info("Extraction complete. %d/%d links found.", valid, len(youtube_links))
            return 0

        # ── Full pipeline ──────────────────────────────────────────────
        credentials = _resolve_credentials(args)
        game = _resolve_game_config(args)
        return _step_uwufufu(
            youtube_links, credentials, game, config, str(config.output_json),
            keep_open=args.keep_browser_open,
        )

    except InvalidInputError as exc:
        return _report_error("Invalid playlist URL", exc)
    except SpotifyError as exc:
        return _report_error("Spotify error", exc)
    except YouTubePlaylistError as exc:
        return _report_error("YouTube playlist error", exc)
    except YouTubeError as exc:
        return _report_error("YouTube error", exc)
    except LoginError as exc:
        return _report_error("Login failed", exc)
    except (NavigationError, GameCreationError) as exc:
        return _report_error("Game creation failed", exc)
    except AutomationError as exc:
        return _report_error("Automation error", exc)
    except UwufufuError as exc:
        return _report_error("Unexpected error", exc)


if __name__ == "__main__":
    sys.exit(main())
