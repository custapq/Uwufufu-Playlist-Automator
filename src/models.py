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
    category_id: int = 16
    """uwufufu category id. 16 = Music (default)."""
    start_time: int = 0
    """Clip start in seconds applied to every video selection."""
    end_time: int = 0
    """Clip end in seconds (0 = full video)."""
    publish: bool = True
    """Set to False to leave the game as a draft after all videos are added."""
    locale: str = "en"
    """Language locale for the game (e.g. en, th, ko)."""
    is_nsfw: bool = False
    """Set to True if the game contains NSFW content."""


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
    """API credentials for Spotify (YouTube uses yt-dlp, no key needed)."""

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://127.0.0.1:8888/callback"
