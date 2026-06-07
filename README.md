# Playlist to UwuFufu Automation Tool (v4.0.1)

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
git clone https://github.com/custapq/Uwufufu-Playlist-Automator.git
cd Uwufufu-Playlist-Automator
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

## 🎮 Creating a Quiz Game (Usage & Game Options)

You can easily automate the creation of a Quiz Game (Worldcup) on UwuFufu. The tool allows you to customize various game options through command-line arguments.

### 1. Recommended Way

The most convenient way is to store your credentials in a `.env` file and use a one-liner command to specify all game details:

```bash
python -m src.main --use-env \
  --playlist-url "https://www.youtube.com/playlist?list=..." \
  --title "Guess The Anime Opening" \
  --description "The ultimate anime song quiz" \
  --category-id 16 \
  --locale "en"
```

### 2. Adjustable Options

You can customize the appearance and visibility of your game using the following parameters:

*   **`--title`**
    *   **Example:** `--title "My Awesome Quiz"`
    *   **Description:** The title of the Worldcup or Quiz that will appear on the website.
*   **`--description`**
    *   **Example:** `--description "Guess the song playing in this video"`
    *   **Description:** The description, rules, or any additional details about the game.
*   **`--locale`**
    *   **Example:** `--locale "en"`, `--locale "th"`, `--locale "ko"`
    *   **Description:** The primary language locale for the game (default is `en`).
*   **`--category-id`**
    *   **Example:** `--category-id 16`
    *   **Description:** The UwuFufu category ID (e.g., 16 = Music). You can find other category IDs via the UwuFufu API `GET /v1/categories` (default is 16).
*   **`--is-nsfw`**
    *   **Example:** `--is-nsfw`
    *   **Description:** Include this flag to mark your game as containing NSFW (Not Safe For Work) or mature content.
*   **Visibility**
    *   **Example:** `--no-publish`
    *   **Description:** By default, the system will set the game's visibility to **Public** automatically once all videos are added. If you want the game to be saved as a **Draft** (hidden), include the `--no-publish` flag.
*   **Clip Times**
    *   **Example:** `--start-time 30 --end-time 60`
    *   **Description:** Apply a global clip time to all videos in the game. It will start playing at `start-time` (seconds) and stop at `end-time` (seconds). If omitted, the full video will be played.

---

### Other Modes

**Interactive Mode**
If you do not provide the above parameters, the program will prompt you interactively step-by-step:
```bash
python -m src.main
```

**Extract Links Only (Spotify / YouTube -> JSON)**
If you only want to extract YouTube links to a `.json` file without uploading to UwuFufu:
```bash
python -m src.main --spotify-only --playlist-url "https://..."
```
> **Note:** For Spotify, on the first run, add the `--spotify-login` flag to authenticate via your browser.

**Resume**
If the program stops unexpectedly, you can resume using the generated `.json` file in the `output/` folder without refetching the playlist:
```bash
python -m src.main --resume output/spotify_to_youtube.json --use-env --title "My Quiz" --description "..."
```

### All Flags Summary

```text
--playlist-url URL    Spotify or YouTube playlist URL
--email EMAIL         UwuFufu account email
--title TEXT          Game title
--description TEXT    Game description
--locale LANG         Language locale, e.g. en, th (default: en)
--category-id N       Category ID (default: 16)
--is-nsfw             Mark as containing NSFW content
--no-publish          Save game as a Draft instead of publishing it
--start-time SECS     Clip start time in seconds
--end-time SECS       Clip end time in seconds
--use-env             Load credentials and Client ID from .env
--spotify-only        Skip the UwuFufu step (extract links only)
--spotify-login       Force a fresh Spotify browser login
--resume FILE         Load YouTube links from JSON to resume UwuFufu import
--config FILE         Path to a custom config.yaml
--output FILE         Base path and filename for the output (no extension)
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
