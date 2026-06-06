from urllib.parse import urlparse

from src.exceptions import InvalidInputError


def detect_source(url: str) -> str:
    """Return 'spotify' or 'youtube' based on the playlist URL host.

    Raises:
        InvalidInputError: If the URL does not match a known playlist provider.
    """
    host = urlparse(url).netloc.lower()
    if "spotify" in host:
        return "spotify"
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    raise InvalidInputError(
        f"Unrecognised playlist URL: '{url}'. "
        "Expected a Spotify (open.spotify.com) or YouTube (youtube.com) playlist link."
    )
