# Playlist to UwuFufu Automation Tool (v3.0.0)

A Python automation tool that takes a **Spotify or YouTube playlist** link, resolves a YouTube video URL for every track, and automatically creates a UwuFufu quiz game with those videos. Just give it one playlist link — it detects the provider for you.

## Features

- **Auto-detects** whether the playlist link is Spotify or YouTube
- Fast and reliable Spotify playlist extraction via the **Spotify API**, then matches each track using **yt-dlp**
- YouTube playlist support that extracts videos **directly** from the playlist using **yt-dlp** (no YouTube API keys or quotas to worry about)
- Creates a UwuFufu game and adds all videos automatically via browser automation
- Saves results to `output/spotify_to_youtube.json` — resume if anything fails
- Supports `.env` file so you never have to type credentials twice
- Headless mode, verbose logging, and flexible CLI flags

## Requirements

- Python 3.8+
- Google Chrome installed
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
You MUST provide the API credentials for Spotify:

1. **Spotify**: Create an app on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) to get a `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
   - **Important**: You must also add `http://127.0.0.1:8888/callback` to the **Redirect URIs** section in your App Settings. This is required for the browser login flow.

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

> `.env` is listed in `.gitignore` and will never be committed.

## ⚠️ Spotify API Limitation (February 2026)

Due to [Spotify API changes in February 2026](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), **you can only fetch tracks from Spotify playlists that you own or collaborate on.** 

- To use a Spotify playlist, you must log in via the browser using the `--spotify-login` flag on your first run. This authorizes the tool to read your playlists.
- Public Spotify playlists owned by others will **not** return any tracks.
- **Alternative**: YouTube playlists do not have this restriction. You can use any public YouTube playlist URL without needing a browser login.

## Usage

### Interactive mode (simplest)

```bash
python -m src.main
```

The tool will prompt for each required value.

### One-liner

```bash
# Works with a Spotify OR a YouTube playlist link — auto-detected
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

### Headless mode (no browser window)

```bash
python -m src.main --headless
```

### Extract links only (skip UwuFufu)

Useful for previewing results before creating a game. Accepts a Spotify or YouTube playlist.
For Spotify, you must use `--spotify-login` on the first run to authorize the app:

```bash
# First time using Spotify (opens browser to log in)
python -m src.main --spotify-login --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

# Subsequent runs (uses cached token)
python -m src.main --spotify-only --playlist-url "https://open.spotify.com/playlist/..."

# YouTube playlists work immediately (no login required)
python -m src.main --spotify-only --playlist-url "https://www.youtube.com/playlist?list=..."
```

Output is saved to `output/spotify_to_youtube.json` and `.txt`.

### Resume after a failure

If the UwuFufu step fails partway through, skip the slow Spotify + YouTube steps and go straight to automation:

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
--headless            Run browser without a visible window
--keep-browser-open   On error, keep Chrome open and pause (for debugging)
--config FILE         Path to a custom config.yaml
--output FILE         Output base path (without extension)
-v / --verbose        Enable debug logging
```

## Project Structure

```
Uwufufu-Automator/
├── src/
│   ├── main.py                  ← Entry point + CLI
│   ├── spotify_api.py           ← Spotify playlist extraction (REST API)
│   ├── youtube_api.py           ← YouTube video search & playlist extraction (yt-dlp)
│   ├── uwufufu_automator.py     ← UwuFufu browser automation
│   ├── file_manager.py          ← Save / load JSON results
│   ├── config.py                ← AppConfig, TimingConfig, SelectorConfig
│   ├── models.py                ← Track, YoutubeLink, Credentials, GameConfig
│   ├── exceptions.py            ← Custom exception hierarchy
│   └── utils/
│       ├── browser.py           ← WebDriver factory + managed_browser context
│       ├── logger.py            ← Logging setup (console + file)
│       ├── retry.py             ← @retry decorator with exponential backoff
│       ├── playlist.py          ← detect_source() — Spotify vs YouTube
│       └── spotify_auth.py      ← Spotify Token Manager
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── requirements-dev.txt
```

## Running Tests

Install the development dependencies first:

```bash
pip install -r requirements-dev.txt
```

Then run the suite:

```bash
pytest                              # run all tests
pytest --cov=src                    # with coverage summary
pytest --cov=src --cov-report=term-missing   # show uncovered lines
```

All tests use mocks — no real network access or browser is required.
Current coverage is ~76% (the API modules sit at 98–100%).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Playlist not loading | Make sure the Spotify/YouTube playlist is set to **Public** |
| `Unrecognised playlist URL` | The link isn't a Spotify or YouTube playlist — check `PLAYLIST_URL` / `--playlist-url` |
| Spotify 403 / no tracks | The playlist must be owned by you. Ensure you used `--spotify-login` and that the redirect URI matches exactly. |
| Login fails | Double-check email and password in `.env` or when prompted |
| Videos not added | UwuFufu may have updated its UI — check `SelectorConfig` in `src/config.py` |
| Browser crashes | Try adding `--headless` flag or updating ChromeDriver |
| Partial failure mid-run | Use `--resume output/spotify_to_youtube.json` to continue without re-fetching |
| Need to inspect a failure | Add `--keep-browser-open` so Chrome stays open and pauses on error |

Log files are written to `logs/automation_YYYYMMDD_HHMMSS.log` for debugging.
