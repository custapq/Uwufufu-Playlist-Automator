"""
config.py — Configuration management สำหรับ Uwufufu-Automator

รวม constants ทั้งหมดที่เดิมกระจายอยู่ใน auto_uwu.py ให้อยู่ในที่เดียว
รองรับการ override ผ่าน config.yaml (ถ้ามี) หรือใช้ค่า default
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# Sub-configs
# ─────────────────────────────────────────────

@dataclass
class TimingConfig:
    """
    ค่า delay ต่างๆ (หน่วย: วินาที) — กำหนดที่เดียว แก้ง่าย

    แทนที่ magic numbers ที่กระจายอยู่ใน auto_uwu.py เดิม เช่น:
      time.sleep(3)   → time.sleep(timing.after_page_submit)
      time.sleep(0.3) → time.sleep(timing.after_click)
    """

    after_login: float = 2.0
    """รอ redirect หลัง login สำเร็จ"""

    after_click: float = 0.3
    """รอ DOM update หลัง click"""

    after_page_submit: float = 3.0
    """รอ server response หลัง submit form"""

    spotify_initial_load: float = 3.0
    """รอ Spotify render หลังโหลดหน้า"""

    between_scroll: float = 1.5
    """รอ infinite scroll โหลด tracks เพิ่ม"""

    youtube_search_min: float = 1.0
    """delay ต่ำสุด ระหว่างค้นหา YouTube แต่ละเพลง"""

    youtube_search_max: float = 2.5
    """delay สูงสุด ระหว่างค้นหา YouTube แต่ละเพลง"""

    between_video_add: float = 0.5
    """รอหลังเพิ่ม video แต่ละตัวใน UwuFufu"""

    reveal_video_input: float = 2.0
    """รอหลังกดปุ่ม video icon ให้ input field ปรากฏ"""

    choices_panel: float = 2.0
    """รอหลังเปิด Choices panel"""


@dataclass
class SelectorConfig:
    """
    CSS selectors และ XPath สำหรับ UwuFufu และ Spotify

    รวมไว้ที่เดียว — เมื่อ UI เปลี่ยน แก้ที่นี่จุดเดียวพอ
    แทนที่ global constants ใน auto_uwu.py เดิม
    """

    # --- UwuFufu Login ---
    login_email: str = "input[name='email']"
    login_password: str = "input[name='password']"
    login_button: str = "button[type='submit']"

    # --- UwuFufu Navigation ---
    create_game_link: str = "a[href='/create-game']"

    # --- UwuFufu Game Form ---
    title_input: str = "input#title"
    description_input: str = "textarea#description"
    choices_button: str = "button[type='submit'].bg-uwu-red.py-2.px-4"
    choices_xpath: str = "//span[normalize-space()='Choices']"

    # --- UwuFufu Video Input ---
    video_icon: str = "svg.lucide-tv-minimal-play"
    youtube_url_input_id: str = "youtubeUrl"
    add_video_button: str = "button.bg-uwu-red[type='submit']"

    # --- Spotify ---
    tracklist_row: str = "[data-testid='tracklist-row']"
    track_link: str = "[data-testid='internal-track-link']"
    artist_link: str = "a[data-testid='artist-link']"
    artists_container: str = "span[data-testid='artists-container']"


# ─────────────────────────────────────────────
# Main Config
# ─────────────────────────────────────────────

@dataclass
class AppConfig:
    """Configuration หลักของแอป — ใช้แทน global constants ใน auto_uwu.py"""

    # --- URLs ---
    uwufufu_url: str = "https://uwufufu.com"
    login_url: str = "https://uwufufu.com/auth/login"
    create_game_url: str = "https://uwufufu.com/create-game"

    # --- Output ---
    output_dir: str = "output"
    output_filename: str = "spotify_to_youtube"

    # --- Browser ---
    headless: bool = False
    window_size: str = "1920,1080"

    # --- Reliability ---
    webdriver_timeout: int = 30
    """วินาที — WebDriverWait timeout"""

    max_retries: int = 3
    """จำนวนครั้งที่ retry เมื่อล้มเหลว"""

    # --- Sub-configs ---
    timing: TimingConfig = field(default_factory=TimingConfig)
    selectors: SelectorConfig = field(default_factory=SelectorConfig)

    @property
    def output_txt(self) -> Path:
        """Path ของ output text file"""
        return Path(self.output_dir) / f"{self.output_filename}.txt"

    @property
    def output_json(self) -> Path:
        """Path ของ output JSON file (สำหรับ resume)"""
        return Path(self.output_dir) / f"{self.output_filename}.json"


# ─────────────────────────────────────────────
# Loader
# ─────────────────────────────────────────────

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    โหลด AppConfig จาก YAML file (ถ้ามี) หรือใช้ค่า default

    Args:
        config_path: path ไปยัง config.yaml (default: "config.yaml")

    Returns:
        AppConfig พร้อมใช้งาน
    """
    path = Path(config_path or "config.yaml")

    if not path.exists():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    timing_data = data.pop("timing", {})
    selectors_data = data.pop("selectors", {})

    timing = TimingConfig(**timing_data) if timing_data else TimingConfig()
    selectors = SelectorConfig(**selectors_data) if selectors_data else SelectorConfig()

    return AppConfig(timing=timing, selectors=selectors, **data)


def load_env_credentials() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    โหลด credentials จาก .env file หรือ environment variables

    Returns:
        (email, password, spotify_url) — None ถ้าไม่มีใน env
    """
    load_dotenv()
    email = os.getenv("UWUFUFU_EMAIL")
    password = os.getenv("UWUFUFU_PASSWORD")
    spotify_url = os.getenv("SPOTIFY_PLAYLIST_URL")
    return email, password, spotify_url
