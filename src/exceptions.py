"""
exceptions.py — Custom exceptions สำหรับ Uwufufu-Automator

เหตุผลที่ใช้ custom exceptions แทน Exception ทั่วไป:
  - จับ exception ได้เฉพาะเจาะจง → error message ชัดเจนขึ้น
  - main() แยก handler ตามประเภทปัญหาได้
  - ง่ายต่อการ debug และ logging
"""


class UwufufuError(Exception):
    """
    Base exception สำหรับทุก error ในโปรแกรมนี้

    ใช้ catch ทั้งหมดใน main():
        except UwufufuError as e:
            logger.error(str(e))
    """


# ─────────────────────────────────────────────
# Spotify
# ─────────────────────────────────────────────

class SpotifyError(UwufufuError):
    """Base exception สำหรับ Spotify-related errors"""


class SpotifyPlaylistNotFoundError(SpotifyError):
    """
    URL ของ Spotify playlist ไม่ถูกต้อง หรือ playlist เป็น private

    วิธีแก้: ตรวจสอบว่า URL ถูกต้องและ playlist เป็น Public
    """


class SpotifyScrapingError(SpotifyError):
    """
    ดึงข้อมูลเพลงจาก Spotify ล้มเหลว (เช่น selector เปลี่ยน)

    วิธีแก้: ตรวจสอบว่า Spotify ไม่ได้เปลี่ยน HTML structure
    """


# ─────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────

class YouTubeError(UwufufuError):
    """Base exception สำหรับ YouTube-related errors"""


class YouTubeSearchError(YouTubeError):
    """
    ค้นหา YouTube ล้มเหลว (เช่น rate limited หรือ network error)

    วิธีแก้: รอสักครู่แล้วลองใหม่, หรือตรวจสอบ internet connection
    """


# ─────────────────────────────────────────────
# UwuFufu Automation
# ─────────────────────────────────────────────

class AutomationError(UwufufuError):
    """Base exception สำหรับ UwuFufu browser automation errors"""


class LoginError(AutomationError):
    """
    Login เข้า UwuFufu ไม่สำเร็จ

    วิธีแก้: ตรวจสอบ email และ password ว่าถูกต้อง
    """


class NavigationError(AutomationError):
    """
    ไม่สามารถ navigate ไปยังหน้าที่ต้องการได้

    วิธีแก้: ตรวจสอบว่า UwuFufu ไม่ได้เปลี่ยน URL structure
    """


class GameCreationError(AutomationError):
    """
    สร้างเกมใหม่บน UwuFufu ไม่สำเร็จ

    วิธีแก้: ตรวจสอบว่า form fields ยังอยู่ตาม selector ที่กำหนด
    """


class ElementNotFoundError(AutomationError):
    """
    หา UI element ไม่เจอ หลัง fallback strategies ทั้งหมดล้มเหลว

    วิธีแก้: อัปเดต selector ใน SelectorConfig ให้ตรงกับ UI ปัจจุบัน
    """


class VideoAddError(AutomationError):
    """
    เพิ่ม YouTube video เข้าเกมไม่สำเร็จ

    วิธีแก้: ตรวจสอบว่า YouTube URL ถูกต้องและ UwuFufu ยังรองรับ URL นั้น
    """


# ─────────────────────────────────────────────
# Config / Input
# ─────────────────────────────────────────────

class ConfigError(UwufufuError):
    """
    ไฟล์ config.yaml มี format ผิดหรือมี field ที่ไม่รู้จัก

    วิธีแก้: ตรวจสอบ config.yaml ให้ตรงกับ AppConfig schema
    """


class InvalidInputError(UwufufuError):
    """
    Input จากผู้ใช้ไม่ถูกต้อง (เช่น Spotify URL format ผิด)

    วิธีแก้: ตรวจสอบ input ให้ถูกต้องตามรูปแบบที่กำหนด
    """
