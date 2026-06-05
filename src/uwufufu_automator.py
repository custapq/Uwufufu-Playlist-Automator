"""
uwufufu_automator.py — UwuFufu browser automation for Uwufufu-Automator

Handles login, game creation, and adding YouTube videos to a UwuFufu game.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Callable, List, Optional, Tuple

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import AppConfig
from src.exceptions import (
    ElementNotFoundError,
    GameCreationError,
    LoginError,
    NavigationError,
    VideoAddError,
)
from src.models import Credentials, GameConfig, YoutubeLink

logger = logging.getLogger(__name__)


class UwuFufuAutomator:
    """Automates UwuFufu game creation and video addition via Selenium."""

    def __init__(self, driver: WebDriver, config: AppConfig) -> None:
        """Initialise the automator with a WebDriver and application config."""
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.webdriver_timeout)
        self._sel = config.selectors
        self._timing = config.timing

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def login(self, credentials: Credentials) -> None:
        """Log in to UwuFufu with the given credentials.

        Raises:
            LoginError: If login fails or the page does not redirect.
        """
        logger.info("Logging into UwuFufu...")
        self.driver.get(self.config.login_url)

        try:
            email_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self._sel.login_email))
            )
            email_input.send_keys(credentials.email)
            time.sleep(self._timing.after_click)

            self.driver.find_element(By.CSS_SELECTOR, self._sel.login_password).send_keys(
                credentials.password
            )
            time.sleep(self._timing.after_click)

            self.driver.find_element(By.CSS_SELECTOR, self._sel.login_button).click()
            self.wait.until(EC.url_contains(self.config.uwufufu_url))
        except WebDriverException as exc:
            raise LoginError(
                "Login failed. Verify that the email and password are correct."
            ) from exc

        logger.info("Logged in successfully")
        time.sleep(self._timing.after_login)

    def navigate_to_create_game(self) -> None:
        """Navigate to the Create Game page using a four-level fallback strategy.

        Raises:
            NavigationError: If all strategies fail.
        """
        logger.info("Navigating to Create Game page...")

        strategies = [
            self._try_create_game_by_selector,
            self._try_create_game_by_text,
            self._try_create_game_by_javascript,
            self._try_create_game_by_direct_navigation,
        ]

        for strategy in strategies:
            if strategy():
                try:
                    self.wait.until(lambda d: "create-game" in d.current_url)
                except WebDriverException:
                    pass
                logger.info("Reached Create Game page")
                return

        raise NavigationError(
            "Could not navigate to the Create Game page. "
            "Check whether UwuFufu has changed its URL structure."
        )

    def fill_game_details(self, game: GameConfig) -> None:
        """Fill in game title and description, then submit the form.

        Raises:
            GameCreationError: If the page does not advance to the game editor.
        """
        logger.info("Filling in game details...")
        time.sleep(self._timing.page_settle)

        title_input = self._find_title_input()
        if title_input:
            title_input.clear()
            time.sleep(self._timing.after_input)
            title_input.send_keys(game.title)
            time.sleep(self._timing.after_input)
        else:
            logger.warning("Could not find title input field")

        description_input = self._find_description_input()
        if description_input:
            description_input.clear()
            time.sleep(self._timing.after_input)
            description_input.send_keys(game.description)
            time.sleep(self._timing.after_input)
        else:
            logger.warning("Could not find description input field")

        submit_btn = self._find_choices_button()
        if submit_btn:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", submit_btn
            )
            time.sleep(self._timing.short_pause)
            try:
                submit_btn.click()
            except WebDriverException:
                self.driver.execute_script("arguments[0].click();", submit_btn)
            logger.info("Submitted game details")
        else:
            logger.warning("Could not find submit button")

        time.sleep(self._timing.after_page_submit)

        if not re.search(r"/create-game/\d+", self.driver.current_url):
            raise GameCreationError(
                f"Unexpected URL after creating game: {self.driver.current_url}"
            )

    def open_choices_panel(self) -> None:
        """Open the Choices panel if it is not already open."""
        logger.info("Opening Choices panel...")
        try:
            choices_el = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, self._sel.choices_xpath))
            )
            time.sleep(self._timing.after_click)
            choices_el.click()
        except WebDriverException:
            logger.debug("Choices panel may already be open")

        time.sleep(self._timing.choices_panel)

    def reveal_video_input(self) -> None:
        """Click the video icon to reveal the YouTube URL input field."""
        logger.info("Revealing video input...")

        if (
            self._try_video_by_selector()
            or self._try_video_by_text()
            or self._try_video_by_javascript()
        ):
            logger.info("Video input revealed")
        else:
            logger.warning("Could not confirm video input was revealed — continuing anyway")

        time.sleep(self._timing.reveal_video_input)

    def add_video(self, link: YoutubeLink) -> bool:
        """Add a single YouTube video to the game.

        Returns:
            True if the video was added successfully, False otherwise.
        """
        inp = self._find_youtube_input()
        if not inp:
            logger.warning("YouTube URL input not found — skipping: %s", link.title)
            return False

        try:
            inp.clear()
            time.sleep(self._timing.after_click)
            inp.send_keys(link.url)
            time.sleep(self._timing.after_click)

            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", inp
            )
            time.sleep(self._timing.after_click)
            inp.send_keys(Keys.TAB)
            time.sleep(self._timing.short_pause)

            if self._click_add_button():
                time.sleep(self._timing.between_video_add)
                return True

            logger.warning("Could not click Add button for: %s", link.title)
            return False
        except WebDriverException as exc:
            logger.warning("Error adding video %s: %s", link.title, exc)
            return False

    def add_all_videos(
        self,
        links: List[YoutubeLink],
        on_added: Optional[Callable[[YoutubeLink], None]] = None,
    ) -> Tuple[int, int]:
        """Add all valid YouTube links to the game.

        Args:
            links:    Links to add.
            on_added: Optional callback invoked with each link right after it is
                      added successfully — used to persist resume progress.

        Returns:
            (success_count, total_count)
        """
        total = len(links)
        success = 0
        for i, link in enumerate(links):
            logger.info("[%d/%d] Adding: %s", i + 1, total, link.title)
            if self.add_video(link):
                success += 1
                link.added = True
                if on_added is not None:
                    on_added(link)

        logger.info("Added %d/%d videos successfully", success, total)
        return success, total

    # ------------------------------------------------------------------ #
    # Navigate to Create Game — fallback strategies
    # ------------------------------------------------------------------ #

    def _try_create_game_by_selector(self) -> bool:
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, self._sel.create_game_link)
            for link in links:
                if link.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", link
                    )
                    time.sleep(self._timing.after_scroll)
                    link.click()
                    logger.debug("Navigated via CSS selector")
                    return True
        except WebDriverException:
            pass
        return False

    def _try_create_game_by_text(self) -> bool:
        try:
            xpath = (
                "//*[contains(text(), 'Create Game') or contains(text(), 'New Game') "
                "or contains(text(), 'create game') or contains(text(), 'new game')]"
            )
            elements = self.driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if element.is_displayed():
                    clickable = element
                    for _ in range(3):
                        tag = self.driver.execute_script(
                            "return arguments[0].tagName;", clickable
                        ).lower()
                        if tag in ("a", "button", "div"):
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", clickable
                            )
                            time.sleep(self._timing.page_settle)
                            self.driver.execute_script("arguments[0].click();", clickable)
                            logger.debug("Navigated via text search")
                            return True
                        clickable = self.driver.execute_script(
                            "return arguments[0].parentNode;", clickable
                        )
        except WebDriverException:
            pass
        return False

    def _try_create_game_by_javascript(self) -> bool:
        try:
            clicked = self.driver.execute_script("""
                function isVisible(el) {
                    if (!el) return false;
                    if (window.getComputedStyle(el).display === 'none') return false;
                    if (window.getComputedStyle(el).visibility === 'hidden') return false;
                    if (el.offsetParent === null) return false;
                    return true;
                }
                for (const link of document.querySelectorAll('a[href="/create-game"], a[href*="create-game"]')) {
                    if (isVisible(link)) { link.click(); return true; }
                }
                const texts = ["Create Game", "New Game", "create game", "new game"];
                for (const text of texts) {
                    for (const el of Array.from(document.querySelectorAll('a, button, div'))) {
                        if (isVisible(el) && el.textContent.includes(text)) {
                            el.click(); return true;
                        }
                    }
                }
                for (const item of document.querySelectorAll('header a, header button, nav a, nav button')) {
                    if (isVisible(item) && (
                        item.textContent.toLowerCase().includes('create') ||
                        item.textContent.toLowerCase().includes('new')
                    )) { item.click(); return true; }
                }
                return false;
            """)
            if clicked:
                logger.debug("Navigated via JavaScript")
                return True
        except WebDriverException:
            pass
        return False

    def _try_create_game_by_direct_navigation(self) -> bool:
        logger.debug("Navigating directly to create-game URL")
        self.driver.get(self.config.create_game_url)
        time.sleep(self._timing.page_settle)
        return True

    # ------------------------------------------------------------------ #
    # Fill game details — element finders
    # ------------------------------------------------------------------ #

    def _find_title_input(self) -> Optional[WebElement]:
        title_input = None
        selectors = [
            self._sel.title_input,
            "input[name='title']",
            "input[placeholder*='title' i]",
            "input[placeholder*='name' i]",
            "input.form-control",
            "input.input",
        ]
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    title_input = el
                    break
            if title_input:
                break

        if not title_input:
            title_input = self.driver.execute_script("""
                const inputs = document.querySelectorAll(
                    'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])'
                );
                for (const input of inputs) {
                    if (input.offsetParent === null) continue;
                    const p = (input.placeholder || '').toLowerCase();
                    const id = (input.id || '').toLowerCase();
                    const n = (input.name || '').toLowerCase();
                    if (p.includes('title') || p.includes('name') ||
                        id.includes('title') || id.includes('name') ||
                        n.includes('title') || n.includes('name') ||
                        input === document.querySelector('form input')) return input;
                }
                for (const input of inputs) {
                    if (input.offsetParent !== null) return input;
                }
                return null;
            """)

        return title_input

    def _find_description_input(self) -> Optional[WebElement]:
        description_input = None
        selectors = [
            self._sel.description_input,
            "textarea[name='description']",
            "textarea[placeholder*='description' i]",
            "textarea",
        ]
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    description_input = el
                    break
            if description_input:
                break

        if not description_input:
            description_input = self.driver.execute_script("""
                const textareas = document.querySelectorAll('textarea');
                for (const t of textareas) {
                    if (t.offsetParent !== null) return t;
                }
                return null;
            """)

        return description_input

    def _find_choices_button(self) -> Optional[WebElement]:
        choices_button = None
        selectors = [
            self._sel.choices_button,
            "button[type='submit']",
            "button.bg-uwu-red",
            "button.btn-primary",
            "input[type='submit']",
        ]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        choices_button = el
                        break
                if choices_button:
                    break
            except WebDriverException:
                continue

        if not choices_button:
            choices_button = self.driver.execute_script("""
                for (const btn of document.querySelectorAll('button[type="submit"]')) {
                    if (btn.offsetParent !== null) return btn;
                }
                for (const text of ['Next', 'Continue', 'Create', 'Submit', 'Save']) {
                    const btns = Array.from(document.querySelectorAll('button')).filter(
                        b => b.offsetParent !== null && b.textContent.includes(text)
                    );
                    if (btns.length > 0) return btns[0];
                }
                return null;
            """)

        return choices_button

    # ------------------------------------------------------------------ #
    # Reveal video input — fallback strategies
    # ------------------------------------------------------------------ #

    def _try_video_by_selector(self) -> bool:
        try:
            icons = self.driver.find_elements(By.CSS_SELECTOR, self._sel.video_icon)
            for icon in icons:
                if icon.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", icon
                    )
                    time.sleep(self._timing.after_click)
                    try:
                        icon.click()
                    except WebDriverException:
                        self.driver.execute_script("arguments[0].click();", icon)
                    return True
        except WebDriverException:
            pass
        return False

    def _try_video_by_text(self) -> bool:
        try:
            elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Video')]")
            for element in elements:
                if element.is_displayed():
                    clickable = element
                    for _ in range(3):
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", clickable
                        )
                        time.sleep(self._timing.short_pause)
                        try:
                            self.driver.execute_script("arguments[0].click();", clickable)
                            return True
                        except WebDriverException:
                            clickable = self.driver.execute_script(
                                "return arguments[0].parentNode;", clickable
                            )
        except WebDriverException:
            pass
        return False

    def _try_video_by_javascript(self) -> bool:
        try:
            clicked = self.driver.execute_script("""
                function isVisible(el) {
                    if (!el) return false;
                    if (window.getComputedStyle(el).display === 'none') return false;
                    if (window.getComputedStyle(el).visibility === 'hidden') return false;
                    if (el.offsetParent === null) return false;
                    return true;
                }
                for (const icon of document.querySelectorAll(
                    'svg.lucide-tv-minimal-play, svg.lucide-video'
                )) {
                    if (isVisible(icon)) {
                        try { icon.click(); return true; } catch(e) {
                            try { icon.parentNode.click(); return true; } catch(e2) {}
                        }
                    }
                }
                const snap = document.evaluate(
                    "//*[contains(text(), 'Video')]", document, null,
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                );
                for (let i = 0; i < snap.snapshotLength; i++) {
                    const el = snap.snapshotItem(i);
                    if (isVisible(el)) {
                        try { el.click(); return true; } catch(e) {
                            let p = el.parentNode;
                            for (let j = 0; j < 3 && p; j++) {
                                try { p.click(); return true; } catch(e2) { p = p.parentNode; }
                            }
                        }
                    }
                }
                for (const btn of document.querySelectorAll('button, div[role="button"]')) {
                    if (isVisible(btn) && (
                        btn.textContent.includes('+') ||
                        btn.textContent.toLowerCase().includes('add') ||
                        btn.textContent.toLowerCase().includes('video')
                    )) { btn.click(); return true; }
                }
                return false;
            """)
            return bool(clicked)
        except WebDriverException:
            pass
        return False

    # ------------------------------------------------------------------ #
    # Add video — helpers
    # ------------------------------------------------------------------ #

    def _find_youtube_input(self) -> Optional[WebElement]:
        try:
            return self.wait.until(
                EC.presence_of_element_located((By.ID, self._sel.youtube_url_input_id))
            )
        except WebDriverException:
            pass

        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        for el in inputs:
            if el.is_displayed():
                placeholder = (el.get_attribute("placeholder") or "").lower()
                if any(kw in placeholder for kw in ("youtube", "url", "video")):
                    return el

        return self.driver.execute_script("""
            const inputs = document.querySelectorAll('input:not([type="hidden"])');
            for (const input of inputs) {
                if (input.offsetParent === null) continue;
                const p = (input.placeholder || '').toLowerCase();
                const id = (input.id || '').toLowerCase();
                const n = (input.name || '').toLowerCase();
                if (p.includes('youtube') || p.includes('url') || p.includes('video') ||
                    id.includes('youtube') || id.includes('url') || id.includes('video') ||
                    n.includes('youtube') || n.includes('url') || n.includes('video')) {
                    return input;
                }
            }
            for (const input of inputs) {
                if (input.offsetParent !== null) return input;
            }
            return null;
        """)

    def _click_add_button(self) -> bool:
        add_buttons = self.driver.find_elements(By.CSS_SELECTOR, self._sel.add_video_button)
        for btn in add_buttons:
            if btn.is_displayed():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn
                )
                time.sleep(self._timing.after_click)
                try:
                    btn.click()
                    return True
                except WebDriverException:
                    pass

        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if btn.is_displayed() and (
                "add" in btn.text.lower()
                or "+" in btn.text
                or btn.get_attribute("type") == "submit"
            ):
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn
                )
                time.sleep(self._timing.after_click)
                try:
                    btn.click()
                    return True
                except WebDriverException:
                    pass

        clicked = self.driver.execute_script("""
            function isVisible(el) {
                if (!el) return false;
                if (window.getComputedStyle(el).display === 'none') return false;
                if (window.getComputedStyle(el).visibility === 'hidden') return false;
                if (el.offsetParent === null) return false;
                return true;
            }
            for (const btn of document.querySelectorAll("button.bg-uwu-red[type='submit']")) {
                if (isVisible(btn)) { btn.click(); return true; }
            }
            for (const btn of document.querySelectorAll("button[type='submit']")) {
                if (isVisible(btn)) { btn.click(); return true; }
            }
            for (const btn of document.querySelectorAll('button')) {
                if (isVisible(btn) && (
                    btn.textContent.toLowerCase().includes('add') ||
                    btn.textContent.includes('+')
                )) { btn.click(); return true; }
            }
            const formBtns = Array.from(document.querySelectorAll('button')).filter(
                b => isVisible(b) && b.closest('form')
            );
            if (formBtns.length > 0) { formBtns[0].click(); return true; }
            return false;
        """)
        return bool(clicked)
