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
        """Return 'Name - Artist' for display and file output."""
        return f"{self.name} - {self.artist}"


@dataclass
class YoutubeLink:
    """The result of matching a Track to a YouTube video."""

    track: Track
    url: Optional[str] = None
    added: bool = False
    """True once this video has been added to UwuFufu (used for --resume)."""

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


@dataclass
class ApiCredentials:
    """API Keys for Spotify and YouTube."""

    spotify_client_id: str
    spotify_client_secret: str
    youtube_api_key: str
