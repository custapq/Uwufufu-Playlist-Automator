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

## 🎮 การสร้าง Quiz Game (Usage & Game Options)

คุณสามารถสร้างเกมทายใจ (Quiz Game) แบบอัตโนมัติบน UwuFufu ได้ง่ายๆ โดยสามารถตั้งค่าตัวเลือกต่างๆ ของเกมได้ตามต้องการผ่านทาง Command Line Arguments ดังนี้

### 1. วิธีที่แนะนำในการรัน (Recommended Way)

วิธีที่สะดวกที่สุดคือการใช้ไฟล์ `.env` สำหรับเก็บรหัสผ่าน และใช้คำสั่งแบบบรรทัดเดียว (One-liner) เพื่อระบุรายละเอียดของเกมทั้งหมด:

```bash
python -m src.main --use-env \
  --playlist-url "https://www.youtube.com/playlist?list=..." \
  --title "Guess The Anime Opening" \
  --description "สุดยอดควิซทายเพลงอนิเมะฮิต" \
  --category-id 16 \
  --locale "th"
```

### 2. ตัวเลือกที่สามารถปรับแต่งได้ (Adjustable Options)

คุณสามารถปรับแต่งหน้าตาและสถานะของเกมได้ผ่าน Parameter เหล่านี้:

*   **`--title` (ชื่อเกม)**
    *   **ตัวอย่าง:** `--title "My Awesome Quiz"`
    *   **คำอธิบาย:** ชื่อของ Worldcup หรือ Quiz ที่จะไปปรากฏบนหน้าเว็บ
*   **`--description` (รายละเอียดเกม)**
    *   **ตัวอย่าง:** `--description "มาทายกันว่าเพลงนี้คือเพลงอะไร"`
    *   **คำอธิบาย:** คำอธิบายรายละเอียดกติกาหรือข้อมูลเกี่ยวกับตัวเกม
*   **`--locale` (ภาษา)**
    *   **ตัวอย่าง:** `--locale "th"`, `--locale "en"`, `--locale "ko"`
    *   **คำอธิบาย:** กำหนดภาษาหลักของตัวเกม (ค่าเริ่มต้นคือ `en`)
*   **`--category-id` (หมวดหมู่ของเกม)**
    *   **ตัวอย่าง:** `--category-id 16`
    *   **คำอธิบาย:** รหัสหมวดหมู่ของ UwuFufu (เช่น 16 = Music) สามารถหาเลข Category อื่นๆ ได้จาก API GET `/v1/categories` ของ UwuFufu (ค่าเริ่มต้นคือ 16)
*   **`--is-nsfw` (เนื้อหาผู้ใหญ่)**
    *   **ตัวอย่าง:** `--is-nsfw`
    *   **คำอธิบาย:** ใส่ Flag นี้เพื่อระบุว่าเกมของคุณมีเนื้อหาล่อแหลม หรือเหมาะสำหรับผู้ใหญ่เท่านั้น
*   **Visibility (สถานะการมองเห็น)**
    *   **ตัวอย่าง:** `--no-publish`
    *   **คำอธิบาย:** โดยปกติระบบจะตั้งสถานะเกมเป็น **Public (สาธารณะ)** โดยอัตโนมัติเมื่อเพิ่มวิดีโอเสร็จสิ้น แต่หากคุณต้องการให้เกมถูกบันทึกเป็นแค่ **Draft (ฉบับร่าง/ซ่อนไว้)** ให้ใส่คำสั่ง `--no-publish` เข้าไปด้วย
*   **Clip Times (การตั้งเวลาเล่นวิดีโอ)**
    *   **ตัวอย่าง:** `--start-time 30 --end-time 60`
    *   **คำอธิบาย:** กำหนดให้วิดีโอทุกตัวในเกมเริ่มเล่นที่วินาทีใด (`start-time`) และหยุดที่วินาทีใด (`end-time`) หากไม่ได้ใส่ระบบจะเล่นวิดีโอแบบเต็มเพลงตั้งแต่ต้น

---

### โหมดการใช้งานอื่นๆ (Other Modes)

**โหมดตอบคำถาม (Interactive Mode)**
หากคุณไม่ได้ใส่ Parameter ข้างต้น โปรแกรมจะโต้ตอบและถามคุณทีละขั้นตอน:
```bash
python -m src.main
```

**ดึงข้อมูลอย่างเดียว ไม่สร้างเกมบน UwuFufu (Spotify / YouTube -> JSON)**
หากต้องการสกัดเฉพาะลิงก์ YouTube ออกมาใส่ไฟล์ `.json` โดยไม่ต้องอัปโหลดขึ้นเว็บ:
```bash
python -m src.main --spotify-only --playlist-url "https://..."
```
> **หมายเหตุ:** สำหรับ Spotify ในการใช้งานครั้งแรกให้ใส่ `--spotify-login` เพิ่มเข้าไป เพื่อทำการล็อกอินผ่าน Browser

**ทำต่อจากที่ค้างไว้ (Resume)**
หากโปรแกรมหยุดทำงานกลางคัน คุณสามารถนำไฟล์ `.json` จากโฟลเดอร์ `output/` มารันต่อได้เลยโดยไม่ต้องไปดึงลิงก์ใหม่จาก Playlist:
```bash
python -m src.main --resume output/spotify_to_youtube.json --use-env --title "My Quiz" --description "..."
```

### สรุปคำสั่ง (All Flags)

```text
--playlist-url URL    ลิงก์ของ Spotify หรือ YouTube Playlist
--email EMAIL         อีเมลของ UwuFufu
--title TEXT          ชื่อเกม
--description TEXT    คำอธิบายเกม
--locale LANG         ภาษาของเกม เช่น en, th (ค่าเริ่มต้น: en)
--category-id N       รหัสหมวดหมู่ (ค่าเริ่มต้น: 16)
--is-nsfw             ติ๊กตั้งค่าว่าเป็นเนื้อหา NSFW
--no-publish          บันทึกเกมเป็น Draft แทนการ Publish สู่สาธารณะ
--start-time SECS     เวลาเริ่มต้นวิดีโอ (วินาที)
--end-time SECS       เวลาสิ้นสุดวิดีโอ (วินาที)
--use-env             โหลดอีเมล/รหัสผ่าน และ Client ID จากไฟล์ .env
--spotify-only        ข้ามขั้นตอน UwuFufu ไปเลย (สกัดลิงก์อย่างเดียว)
--spotify-login       บังคับล็อกอินเข้า Spotify ผ่านหน้าเว็บใหม่
--resume FILE         โหลดลิงก์ YouTube จากไฟล์ JSON เพื่อทำต่อ
--config FILE         ระบุที่อยู่ของไฟล์ config.yaml
--output FILE         ระบุ path และชื่อไฟล์ผลลัพธ์ที่จะเซฟ (ไม่ต้องใส่นามสกุล)
-v / --verbose        เปิดระบบ Debug Logging
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
