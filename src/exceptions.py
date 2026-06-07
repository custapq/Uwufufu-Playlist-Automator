class UwufufuError(Exception):
    """Base exception for all errors raised by this program."""


# ─────────────────────────────────────────────
# Spotify
# ─────────────────────────────────────────────

class SpotifyError(UwufufuError):
    """Base exception for Spotify-related errors."""


class SpotifyPlaylistNotFoundError(SpotifyError):
    """Spotify playlist URL is invalid or the playlist is private."""


class SpotifyScrapingError(SpotifyError):
    """Failed to extract track data from Spotify."""


class SpotifyPlaylistAccessError(SpotifyError):
    """Spotify returned playlist metadata but not its tracks.

    Since February 2026, playlist contents require the authenticated user to own
    or collaborate on the playlist. Use ``--spotify-login`` or a YouTube playlist.
    """


# ─────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────

class YouTubeError(UwufufuError):
    """Base exception for YouTube-related errors."""


class YouTubeSearchError(YouTubeError):
    """YouTube search failed (e.g. rate limited or network error)."""


class YouTubePlaylistError(YouTubeError):
    """Failed to fetch a YouTube playlist (private or invalid URL)."""


# ─────────────────────────────────────────────
# UwuFufu API
# ─────────────────────────────────────────────

class AutomationError(UwufufuError):
    """Base exception for UwuFufu API errors."""


class LoginError(AutomationError):
    """Login to UwuFufu failed — verify email and password."""


class NavigationError(AutomationError):
    """Unused in v4; kept for import compatibility."""


class GameCreationError(AutomationError):
    """Creating or publishing a game on UwuFufu failed."""


class ElementNotFoundError(AutomationError):
    """Unused in v4; kept for import compatibility."""


class VideoAddError(AutomationError):
    """Failed to add a YouTube video to the game."""


# ─────────────────────────────────────────────
# Config / Input
# ─────────────────────────────────────────────

class ConfigError(UwufufuError):
    """config.yaml is malformed or required env vars are missing."""


class InvalidInputError(UwufufuError):
    """User-provided input is invalid (e.g. a malformed playlist URL)."""
