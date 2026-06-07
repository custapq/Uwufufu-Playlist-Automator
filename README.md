# Playlist to UwuFufu Automation Tool (v4.0.0)

A Python automation tool that takes a **Spotify or YouTube playlist** link, resolves a YouTube video URL for every track, and automatically creates a UwuFufu quiz game with those videos via the **UwuFufu REST API** — no browser or ChromeDriver required.

> **v3 (Selenium-based)** is preserved on the [`v3` branch](https://github.com/custapq/Uwufufu-Automator/tree/v3) for reference.

## Features

- **Auto-detects** whether the playlist link is Spotify or YouTube
- Fast and reliable Spotify playlist extraction via the **Spotify API**, then matches each track using **yt-dlp**
- YouTube playlist support that extracts videos **directly** from the playlist using **yt-dlp** (no YouTube API key required)
- Creates a UwuFufu game and adds all videos via the **UwuFufu REST API** (fast, no browser needed)
- Optional clip times (`--start-time` / `--end-time`) applied to every video
- Saves results to `output/spotify_to_youtube.json` — resume if anything fails
- Supports `.env` file so you never have to type credentials twice
- Verbose logging and flexible CLI flags

## Requirements

- Python 3.8+
- Internet connection

## Installation

```bash
git clone https://github.com/custapq/Uwufufu-Automator.git
cd Uwufufu-Automator
pip install -r requirements.txt
```

For running tests:

```bash
pip install -r requirements-dev.txt
```

## Configuration (required)

Copy `.env.example` to `.env` and fill in your credentials so the tool loads them automatically.

```ini
# --- UwuFufu Credentials ---
UWUFUFU_EMAIL=your_email@example.com
UWUFUFU_PASSWORD=your_password

# --- Playlist URL (Spotify or YouTube — the tool auto-detects) ---
PLAYLIST_URL=https://open.spotify.com/playlist/xxxxx

# --- Spotify API Credentials ---
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

**Spotify setup:** Create an app on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and add `http://127.0.0.1:8888/callback` to the **Redirect URIs** in your App Settings.

> `.env` is listed in `.gitignore` and will never be committed.

## ⚠️ Spotify API Limitation (February 2026)

Due to [Spotify API changes in February 2026](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), **you can only fetch tracks from Spotify playlists that you own or collaborate on.**

- Use `--spotify-login` on your first run to log in via browser and authorize the tool.
- Public Spotify playlists owned by others will **not** return any tracks.
- **Alternative**: YouTube playlists have no such restriction — any public playlist works.

## Usage

### Interactive mode (simplest)

```bash
python -m src.main
```

The tool will prompt for each required value.

### One-liner

```bash
python -m src.main \
  --playlist-url "https://open.spotify.com/playlist/..." \
  --email "user@example.com" \
  --title "My Music Quiz" \
  --description "Guess the song!"
```

### Load credentials from `.env`

```bash
python -m src.main --use-env --title "My Quiz" --description "Best songs"
```

### Set game category and clip times

```bash
# Category 16 = Music (default). Find others with GET /v1/categories on the API.
python -m src.main --use-env --title "My Quiz" --description "..." \
  --category-id 16 \
  --start-time 0 \
  --end-time 30
```

### Save as draft (don't publish)

```bash
python -m src.main --use-env --title "My Quiz" --description "..." --no-publish
```

### Extract links only (skip UwuFufu)

```bash
# First time using Spotify (opens browser to log in)
python -m src.main --spotify-login --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

# Subsequent runs (uses cached token)
python -m src.main --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

# YouTube playlists work immediately (no login required)
python -m src.main --spotify-only --playlist-url "https://www.youtube.com/playlist?list=..."
```

### Resume after a failure

If the import step fails partway through, skip the Spotify + YouTube steps and go straight to the API import:

```bash
python -m src.main --resume output/spotify_to_youtube.json \
  --email "user@example.com" \
  --title "My Quiz" \
  --description "Best songs"
```

### All flags

```
--playlist-url URL    Spotify or YouTube playlist URL (provider auto-detected)
--email EMAIL         UwuFufu account email
--title TEXT          Game title
--description TEXT    Game description
--use-env             Load credentials from .env
--spotify-only        Stop after saving YouTube links (skip UwuFufu)
--spotify-login       Force a fresh Spotify browser login (Authorization Code flow)
--resume FILE         Load YouTube links from JSON and skip to UwuFufu step
--category-id N       UwuFufu category id (default: 16 = Music)
--start-time SECS     Clip start in seconds for every video (default: 0)
--end-time SECS       Clip end in seconds — 0 means full video (default: 0)
--no-publish          Leave the game as a draft instead of publishing
--config FILE         Path to a custom config.yaml
--output FILE         Output base path (without extension)
-v / --verbose        Enable debug logging
```

## Project Structure

```
Uwufufu-Automator/
├── src/
│   ├── main.py                  ← Entry point + CLI
│   ├── uwufufu_api.py           ← UwuFufu REST API client (login / create / add / publish)
│   ├── spotify_api.py           ← Spotify playlist extraction
│   ├── youtube_api.py           ← YouTube video search & playlist extraction (yt-dlp)
│   ├── file_manager.py          ← Save / load JSON results
│   ├── config.py                ← AppConfig
│   ├── models.py                ← Track, YoutubeLink, Credentials, GameConfig
│   ├── exceptions.py            ← Custom exception hierarchy
│   └── utils/
│       ├── logger.py            ← Logging setup (console + file)
│       ├── retry.py             ← @retry decorator with exponential backoff
│       ├── playlist.py          ← detect_source() — Spotify vs YouTube
│       ├── spotify_auth.py      ← Spotify Token Manager (Client Credentials)
│       └── spotify_oauth.py     ← Spotify User Auth (Authorization Code flow)
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── requirements-dev.txt
```

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest                              # run all tests
pytest --cov=src                    # with coverage summary
```

All tests use mocks — no real network access or UwuFufu account is required.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Playlist not loading | Make sure the Spotify/YouTube playlist is set to **Public** |
| `Unrecognised playlist URL` | Check `PLAYLIST_URL` / `--playlist-url` format |
| Spotify 403 / no tracks | Playlist must be owned by you. Use `--spotify-login` and verify the redirect URI matches. |
| Login fails | Double-check email and password — UwuFufu password must be 8–50 characters |
| Videos not added | Check that the YouTube URL is valid and publicly accessible |
| Partial failure mid-run | Use `--resume output/spotify_to_youtube.json` to continue |

Log files are written to `logs/automation_YYYYMMDD_HHMMSS.log` for debugging.
