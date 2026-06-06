import logging
from typing import List

import yt_dlp

from src.exceptions import YouTubePlaylistError, YouTubeSearchError
from src.models import Track, YoutubeLink, ApiCredentials

logger = logging.getLogger(__name__)

_DELETED_TITLES = {"Deleted video", "Private video"}


class YouTubeAPI:
    """Fetches YouTube playlist tracks and searches for videos via yt-dlp."""

    def __init__(self, api_creds: ApiCredentials = None) -> None:
        """Initialise the API client (api_creds are no longer required but kept for compatibility)."""
        pass

    def get_playlist_tracks(self, playlist_url: str) -> List[YoutubeLink]:
        """Return all videos from a public YouTube playlist as YoutubeLink objects.

        Raises:
            YouTubePlaylistError: If the playlist cannot be extracted.
        """
        logger.info("Fetching videos from YouTube playlist via yt-dlp: %s", playlist_url)

        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        links: List[YoutubeLink] = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(playlist_url, download=False)
                if not result:
                    raise YouTubePlaylistError("No data returned from yt-dlp for the playlist.")
                
                entries = result.get('entries', [])
                for entry in entries:
                    if not entry:
                        continue
                        
                    title = entry.get('title', '')
                    channel = entry.get('uploader', '')
                    url = entry.get('url')
                    
                    if not url or title in _DELETED_TITLES:
                        continue
                        
                    # Some flat extractions don't give a full URL but only an ID
                    if not url.startswith("http"):
                        url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                        
                    links.append(YoutubeLink(track=Track(name=title, artist=channel), url=url))

        except Exception as exc:
            raise YouTubePlaylistError(f"Failed to fetch YouTube playlist: {exc}") from exc

        if not links:
            raise YouTubePlaylistError("Playlist was found but returned no playable videos.")

        logger.info("Extracted %d videos from YouTube playlist", len(links))
        return links

    def search_all(self, tracks: List[Track]) -> List[YoutubeLink]:
        """Search YouTube for every track; return one YoutubeLink per track."""
        results: List[YoutubeLink] = []
        total = len(tracks)
        logger.info("Searching YouTube for %d tracks via yt-dlp...", total)

        for i, track in enumerate(tracks):
            logger.info("[%d/%d] Searching: %s", i + 1, total, track)
            link = self.search(track)
            results.append(link)

        found = sum(1 for r in results if r.is_valid)
        logger.info("YouTube search complete: %d/%d found", found, total)
        return results

    def search(self, track: Track) -> YoutubeLink:
        """Search YouTube for a single track and return a YoutubeLink.

        Raises:
            YouTubeSearchError: If yt-dlp fails to execute the search.
        """
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        search_query = f"ytsearch1:{track.search_query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=False)
                entries = result.get('entries', []) if result else []
                
                if entries and entries[0]:
                    entry = entries[0]
                    video_id = entry.get('id')
                    
                    if video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        logger.debug("Found: %s → %s", track, video_url)
                        return YoutubeLink(track=track, url=video_url)
                        
        except Exception as exc:
            logger.error("YouTube search failed for '%s': %s", track.search_query, exc)
            raise YouTubeSearchError(f"YouTube search request failed: {exc}") from exc

        logger.warning("No YouTube video found for: %s", track)
        return YoutubeLink(track=track, url=None)
