"""
browser.py — WebDriver factory and browser utilities for Uwufufu-Automator
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Strategy tuple: (By constant, selector string, human-readable description)
Strategy = Tuple[str, str, str]


def create_driver(headless: bool = False, window_size: str = "1920,1080") -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument(f"--window-size={window_size}")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")

    if headless:
        chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=chrome_options)
    logger.debug("Chrome WebDriver created (headless=%s, window=%s)", headless, window_size)
    return driver


def find_element_with_fallback(
    driver: WebDriver,
    strategies: List[Strategy],
) -> Optional[WebElement]:
    """Try each (By, selector, description) strategy in order; return the first visible element found.

    Returns None if no strategy succeeds.
    """
    for by, selector, description in strategies:
        try:
            elements = driver.find_elements(by, selector)
            for element in elements:
                if element.is_displayed():
                    logger.debug("Element found via: %s", description)
                    return element
        except WebDriverException:
            continue

    logger.debug("Element not found after trying %d strategies", len(strategies))
    return None


@contextmanager
def managed_browser(
    headless: bool = False,
    window_size: str = "1920,1080",
    timeout: int = 30,
    keep_open_on_error: bool = False,
) -> Generator[Tuple[WebDriver, WebDriverWait], None, None]:
    """Context manager that creates a Chrome driver and guarantees driver.quit() on exit.

    Args:
        headless:           Run Chrome without a visible window.
        window_size:        Browser window size, e.g. "1920,1080".
        timeout:            WebDriverWait timeout in seconds.
        keep_open_on_error: If True (and not headless), pause for Enter before
                            closing the browser when an exception occurs — useful
                            for inspecting the page state that caused a failure.

    Yields:
        (driver, wait) — the WebDriver instance and a pre-configured WebDriverWait.

    Example::

        with managed_browser(headless=True) as (driver, wait):
            driver.get("https://example.com")
    """
    driver = create_driver(headless=headless, window_size=window_size)
    wait = WebDriverWait(driver, timeout)
    try:
        yield driver, wait
    except BaseException:
        if keep_open_on_error and not headless:
            logger.warning("An error occurred — leaving the browser open for inspection.")
            input("Press Enter to close the browser...")
        raise
    finally:
        driver.quit()
        logger.debug("Chrome WebDriver closed")
