"""
models.py — Data classes for Uwufufu-Automator

Replaces plain dicts used in the original auto_uwu.py to provide:
- Type safety  — IDE warns when accessing wrong fields
- Readability  — each field's purpose is self-documenting
- Testability  — model logic can be unit-tested in isolation
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Track:
    """A single track extracted from a Spotify playlist."""

    name: str
    artist: str

    @property
    def search_query(self) -> str:
        """Query string used for YouTube search."""
        return f"{self.name} {self.artist}"

    def __str__(self) -> str:
        return f"{self.name} - {self.artist}"


@dataclass
class YoutubeLink:
    """The result of matching a Track to a YouTube video."""

    track: Track
    url: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """True when a YouTube URL was found for this track."""
        return self.url is not None

    @property
    def title(self) -> str:
        """Display title in the format 'Track Name - Artist'."""
        return str(self.track)


@dataclass
class GameConfig:
    """Configuration for a new UwuFufu game."""

    title: str
    description: str


@dataclass
class Credentials:
    """Login credentials for UwuFufu."""

    email: str
    password: str


@dataclass
class UserInput:
    """All user-provided inputs bundled together."""

    spotify_url: str
    credentials: Credentials
    game: GameConfig
