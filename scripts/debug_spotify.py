"""Standalone Spotify API tester — isolate why a playlist call fails.

Run from the repo root:

    python scripts/debug_spotify.py "https://open.spotify.com/playlist/XXXX"

If no URL is given it falls back to PLAYLIST_URL in your .env.
It reuses your real credentials/token, then hits three variants of the
playlist endpoint so you can see exactly which one Spotify rejects (and
whether the `market` param is the culprit).
"""

import sys
from pathlib import Path

import requests

# Make `src` importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_api_credentials, load_env_credentials  # noqa: E402
from src.spotify_api import SpotifyAPI  # noqa: E402
from src.utils.spotify_auth import SpotifyTokenManager  # noqa: E402


def _show(label: str, response: requests.Response) -> None:
    print(f"\n=== {label} ===")
    print("status:", response.status_code)
    print(response.text[:500])


def main() -> None:
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        _email, _pw, url = load_env_credentials()
    if not url:
        print("No playlist URL given and PLAYLIST_URL not set in .env")
        sys.exit(1)

    creds = load_api_credentials()
    token_manager = SpotifyTokenManager(creds)
    token = token_manager.get_token()
    print("Token acquired:", token[:12] + "...")

    playlist_id = SpotifyAPI(token_manager)._extract_playlist_id(url)
    print("Playlist ID:", playlist_id or "(could not extract)")

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    base = f"https://api.spotify.com/v1/playlists/{playlist_id}"

    # 1) playlist metadata (tells us if the playlist itself is reachable)
    _show("GET /playlists/{id}", requests.get(base, headers=headers))

    # 2) tracks WITH market=ES (what the app currently sends)
    _show(
        "GET /playlists/{id}/tracks?market=ES",
        requests.get(f"{base}/tracks", headers=headers,
                     params={"market": "ES", "limit": 5}),
    )

    # 3) tracks WITHOUT market (does dropping market fix the 403?)
    _show(
        "GET /playlists/{id}/tracks (no market)",
        requests.get(f"{base}/tracks", headers=headers, params={"limit": 5}),
    )

    # 4) BASE endpoint, NO fields filter — inspect the embedded tracks object
    #    directly to see whether track data is readable at all for this app.
    r = requests.get(base, headers=headers)
    print("\n=== GET /playlists/{id} (no fields) -> inspect .tracks ===")
    print("status:", r.status_code)
    if r.status_code == 200:
        tracks = r.json().get("tracks") or {}
        items = tracks.get("items", [])
        print("tracks.total:", tracks.get("total"))
        print("tracks.items length on this page:", len(items))
        print("tracks.next:", tracks.get("next"))
        names = [
            f'{i["track"]["name"]} - {", ".join(a["name"] for a in i["track"]["artists"])}'
            for i in items[:5]
            if i.get("track")
        ]
        print("first few:", names)
    else:
        print(r.text[:300])


if __name__ == "__main__":
    main()
