# Spotify to UwuFufu Automation Tool (v3.0.0)

A Python automation tool that extracts tracks from a public Spotify playlist, finds matching YouTube videos for each track, and automatically creates a UwuFufu quiz game with those videos.

## Features

- Fast and reliable Spotify playlist extraction via the **Spotify API**
- Fast and accurate YouTube video search via the **YouTube Data API v3**
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
You MUST provide the API keys for Spotify and YouTube:

1. **Spotify**: Create an app on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) to get a `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
2. **YouTube**: Create a project on the [Google Cloud Console](https://console.cloud.google.com/), enable the **YouTube Data API v3**, and generate a `YOUTUBE_API_KEY`.

```ini
# --- UwuFufu Credentials ---
UWUFUFU_EMAIL=your_email@example.com
UWUFUFU_PASSWORD=your_password

# --- Spotify Playlist ---
SPOTIFY_PLAYLIST_URL=https://open.spotify.com/playlist/xxxxx

# --- Spotify API Credentials ---
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# --- YouTube API Credentials ---
YOUTUBE_API_KEY=your_youtube_api_key_here
```

> `.env` is listed in `.gitignore` and will never be committed.

## Usage

### Interactive mode (simplest)

```bash
python -m src.main
```

The tool will prompt for each required value.

### One-liner

```bash
python -m src.main \
  --spotify-url "https://open.spotify.com/playlist/..." \
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

### Spotify + YouTube only (skip UwuFufu)

Useful for previewing results before creating a game:

```bash
python -m src.main --spotify-only --spotify-url "https://open.spotify.com/playlist/..."
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
--spotify-url URL     Spotify playlist URL
--email EMAIL         UwuFufu account email
--title TEXT          Game title
--description TEXT    Game description
--use-env             Load credentials from .env
--spotify-only        Stop after saving YouTube links (skip UwuFufu)
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
│   ├── youtube_api.py           ← YouTube video search (REST API)
│   ├── uwufufu_automator.py     ← UwuFufu browser automation
│   ├── file_manager.py          ← Save / load JSON results
│   ├── config.py                ← AppConfig, TimingConfig, SelectorConfig
│   ├── models.py                ← Track, YoutubeLink, Credentials, GameConfig
│   ├── exceptions.py            ← Custom exception hierarchy
│   └── utils/
│       ├── browser.py           ← WebDriver factory + managed_browser context
│       ├── logger.py            ← Logging setup (console + file)
│       ├── retry.py             ← @retry decorator with exponential backoff
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
Current coverage is ~67% (the frozen `auto_uwu_legacy.py` is excluded via `.coveragerc`).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Spotify playlist not loading | Make sure the playlist is set to **Public** |
| Login fails | Double-check email and password in `.env` or when prompted |
| Videos not added | UwuFufu may have updated its UI — check `SelectorConfig` in `src/config.py` |
| YouTube search returns nothing | YouTube HTML structure may have changed — check `_VIDEO_ID_RE` in `src/youtube_searcher.py` |
| Browser crashes | Try adding `--headless` flag or updating ChromeDriver |
| Partial failure mid-run | Use `--resume output/spotify_to_youtube.json` to continue without re-scraping |
| Need to inspect a failure | Add `--keep-browser-open` so Chrome stays open and pauses on error |

Log files are written to `logs/automation_YYYYMMDD_HHMMSS.log` for debugging.
