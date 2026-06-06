class UwufufuError(Exception):
    """
    Base exception for all errors raised by this program.

    Use this to catch everything in main():
        except UwufufuError as e:
            logger.error(str(e))
    """


# ─────────────────────────────────────────────
# Spotify
# ─────────────────────────────────────────────

class SpotifyError(UwufufuError):
    """Base exception for Spotify-related errors."""


class SpotifyPlaylistNotFoundError(SpotifyError):
    """
    The Spotify playlist URL is invalid or the playlist is private.

    Fix: verify the URL is correct and the playlist visibility is set to Public.
    """


class SpotifyScrapingError(SpotifyError):
    """
    Failed to extract track data from Spotify (e.g. selectors changed).

    Fix: check whether Spotify has updated its HTML structure and update SelectorConfig.
    """


class SpotifyPlaylistAccessError(SpotifyError):
    """
    Spotify returned the playlist's metadata but not its tracks.

    Since Spotify's February 2026 API changes, playlist contents are only
    returned for playlists the authenticated user owns or collaborates on.
    Client Credentials (app-only) cannot read any playlist's tracks.

    Fix: log in with ``--spotify-login`` and use a playlist you own, or use a
    YouTube playlist instead.
    """


# ─────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────

class YouTubeError(UwufufuError):
    """Base exception for YouTube-related errors."""


class YouTubeSearchError(YouTubeError):
    """
    YouTube search failed (e.g. rate limited or network error).

    Fix: wait a moment and retry, or check your internet connection.
    """


class YouTubePlaylistError(YouTubeError):
    """
    Failed to fetch a YouTube playlist (e.g. playlist is private or ID is invalid).

    Fix: make sure the playlist is set to Public and the URL is correct.
    """


# ─────────────────────────────────────────────
# UwuFufu Automation
# ─────────────────────────────────────────────

class AutomationError(UwufufuError):
    """Base exception for UwuFufu browser automation errors."""


class LoginError(AutomationError):
    """
    Login to UwuFufu failed.

    Fix: verify that the email and password are correct.
    """


class NavigationError(AutomationError):
    """
    Could not navigate to the required page.

    Fix: check whether UwuFufu has changed its URL structure.
    """


class GameCreationError(AutomationError):
    """
    Creating a new game on UwuFufu failed.

    Fix: verify that the form fields still match the selectors in SelectorConfig.
    """


class ElementNotFoundError(AutomationError):
    """
    A UI element could not be found after exhausting all fallback strategies.

    Fix: update the relevant selector in SelectorConfig to match the current UI.
    """


class VideoAddError(AutomationError):
    """
    Failed to add a YouTube video to the game.

    Fix: verify the YouTube URL is valid and still supported by UwuFufu.
    """


# ─────────────────────────────────────────────
# Config / Input
# ─────────────────────────────────────────────

class ConfigError(UwufufuError):
    """
    config.yaml is malformed or contains unknown fields.

    Fix: review config.yaml and ensure it matches the AppConfig schema.
    """


class InvalidInputError(UwufufuError):
    """
    User-provided input is invalid (e.g. a malformed Spotify URL).

    Fix: ensure the input follows the expected format.
    """
