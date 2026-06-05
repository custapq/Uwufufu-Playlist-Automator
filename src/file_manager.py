"""
file_manager.py — Save and load YouTube link results for Uwufufu-Automator
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from src.models import Track, YoutubeLink

logger = logging.getLogger(__name__)


def save_youtube_links(links: List[YoutubeLink], output_dir: str, filename: str) -> None:
    """Save YouTube links to both a JSON file and a human-readable text file.

    Args:
        links:      List of YoutubeLink objects to save.
        output_dir: Directory where files are written (created if absent).
        filename:   Base filename without extension (e.g. 'spotify_to_youtube').
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    json_path = dir_path / f"{filename}.json"
    txt_path = dir_path / f"{filename}.txt"

    data = [
        {
            "track_name": link.track.name,
            "artist": link.track.artist,
            "url": link.url,
            "added_to_uwufufu": False,
        }
        for link in links
    ]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(txt_path, "w", encoding="utf-8") as f:
        for link in links:
            status = link.url if link.is_valid else "No video found"
            f.write(f"{link.title}: {status}\n")

    logger.info("Saved %d links → %s (JSON + TXT)", len(links), dir_path)


def load_youtube_links(json_path: str) -> List[YoutubeLink]:
    """Load YouTube links from a JSON file produced by save_youtube_links().

    Args:
        json_path: Path to the .json file.

    Returns:
        List of YoutubeLink objects.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    links = [
        YoutubeLink(
            track=Track(name=item["track_name"], artist=item["artist"]),
            url=item.get("url"),
        )
        for item in data
    ]

    logger.info("Loaded %d links from %s", len(links), json_path)
    return links


def mark_video_added(json_path: str, track_name: str, artist: str) -> None:
    """Mark a single track as added_to_uwufufu=True in the JSON checkpoint file.

    Called after each successful video add so that --resume can skip it.
    """
    path = Path(json_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        if item["track_name"] == track_name and item["artist"] == artist:
            item["added_to_uwufufu"] = True
            break

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
