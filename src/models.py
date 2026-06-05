"""
models.py — Data classes สำหรับ Uwufufu-Automator

แทนที่การใช้ dict ธรรมดาในโค้ดเดิม เพื่อให้:
- Type safety — IDE แจ้งเตือนเมื่อใช้ field ผิด
- Readability — ชัดเจนว่าข้อมูลแต่ละตัวคืออะไร
- Testability — ทดสอบ logic ของ model แยกได้
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Track:
    """ข้อมูลเพลงที่ดึงมาจาก Spotify playlist"""

    name: str
    artist: str

    @property
    def search_query(self) -> str:
        """Query string สำหรับค้นหาใน YouTube"""
        return f"{self.name} {self.artist}"

    def __str__(self) -> str:
        return f"{self.name} - {self.artist}"


@dataclass
class YoutubeLink:
    """ผลลัพธ์การจับคู่ Track กับ YouTube video"""

    track: Track
    url: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """True ถ้ามี YouTube URL (ค้นหาเจอ)"""
        return self.url is not None

    @property
    def title(self) -> str:
        """ชื่อที่ใช้แสดงผล: 'Track Name - Artist'"""
        return str(self.track)


@dataclass
class GameConfig:
    """ข้อมูลสำหรับสร้างเกมบน UwuFufu"""

    title: str
    description: str


@dataclass
class Credentials:
    """ข้อมูล login สำหรับ UwuFufu"""

    email: str
    password: str


@dataclass
class UserInput:
    """รวม input ทั้งหมดที่ผู้ใช้กรอก"""

    spotify_url: str
    credentials: Credentials
    game: GameConfig
