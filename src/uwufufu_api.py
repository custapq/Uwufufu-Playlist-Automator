from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import requests

from src.exceptions import (
    ConfigError,
    GameCreationError,
    LoginError,
    VideoAddError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.uwufufu.com/v1"

# Status codes that are safe to retry on.
_RETRYABLE = {429, 500, 502, 503, 504}


@dataclass
class GameInfo:
    id: int
    slug: Optional[str]


@dataclass
class ImportResult:
    game_id: int
    slug: Optional[str]
    created: bool
    added: int
    skipped: int
    failed: int


class UwufufuAPIError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class UwufufuAPIClient:
    """Thin HTTP client for the uwufufu REST API (https://api.uwufufu.com/v1).

    Mirrors the TypeScript SDK in Uwufufu-API but implemented with ``requests``
    so the Automator stays pure-Python with no Node dependency.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        max_retries: int = 2,
        retry_base_delay: float = 0.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._session = session or requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self._token: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #

    def login(self, email: str, password: str) -> str:
        """POST /auth/login → store and return accessToken.

        Raises:
            LoginError: if credentials are rejected (401/400) or network fails.
        """
        try:
            data = self._request("POST", "/auth/login", json={"email": email, "password": password})
        except UwufufuAPIError as exc:
            raise LoginError(
                "Login failed. Verify that the email and password are correct."
            ) from exc
        except requests.RequestException as exc:
            raise LoginError(f"Network error during login: {exc}") from exc

        token: str = data["accessToken"]
        self._token = token
        self._session.headers["Authorization"] = f"Bearer {token}"
        logger.info("Logged in to UwuFufu successfully")
        return token

    # ------------------------------------------------------------------ #
    # Games
    # ------------------------------------------------------------------ #

    def create_game(
        self,
        title: str,
        description: str,
        category_id: int,
        is_nsfw: bool = False,
    ) -> GameInfo:
        """POST /games → draft worldcup.

        Raises:
            GameCreationError: on API or network failure.
        """
        try:
            data = self._request(
                "POST",
                "/games",
                json={
                    "title": title,
                    "description": description,
                    "categoryId": category_id,
                    "isNsfw": is_nsfw,
                    "visibility": "IS_CLOSED",
                },
            )
        except (UwufufuAPIError, requests.RequestException) as exc:
            raise GameCreationError(f"Failed to create game: {exc}") from exc

        return GameInfo(id=int(data["id"]), slug=data.get("slug"))

    def publish_game(
        self,
        game_id: int,
        category_id: int,
        locale: str = "en",
    ) -> None:
        """PUT /games/:id — set visibility to IS_PUBLIC.

        Raises:
            GameCreationError: on API or network failure.
        """
        try:
            self._request(
                "PUT",
                f"/games/{game_id}",
                json={
                    "id": game_id,
                    "visibility": "IS_PUBLIC",
                    "categoryId": category_id,
                    "locale": locale,
                },
            )
        except (UwufufuAPIError, requests.RequestException) as exc:
            raise GameCreationError(f"Failed to publish game {game_id}: {exc}") from exc

        logger.info("Game %d published", game_id)

    # ------------------------------------------------------------------ #
    # Selections
    # ------------------------------------------------------------------ #

    def add_video(
        self,
        worldcup_id: int,
        url: str,
        start_time: int = 0,
        end_time: int = 0,
    ) -> Dict[str, Any]:
        """POST /selections/video — add a YouTube video to a worldcup.

        Raises:
            VideoAddError: on API or network failure.
        """
        try:
            return self._request(
                "POST",
                "/selections/video",
                json={
                    "worldcupId": worldcup_id,
                    "url": url,
                    "startTime": start_time,
                    "endTime": end_time,
                },
            )
        except (UwufufuAPIError, requests.RequestException) as exc:
            raise VideoAddError(f"Failed to add video {url}: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Categories
    # ------------------------------------------------------------------ #

    def list_categories(self) -> List[Dict[str, Any]]:
        """GET /categories — returns list of {id, name} dicts."""
        return self._request("GET", "/categories")  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # High-level: import tracks
    # ------------------------------------------------------------------ #

    def import_tracks(
        self,
        tracks: list,
        *,
        game_id: Optional[int] = None,
        create: Optional[Dict[str, Any]] = None,
        start_time: int = 0,
        end_time: int = 0,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> ImportResult:
        """Import a list of YoutubeLink objects into a worldcup.

        Args:
            tracks:      List of YoutubeLink. Rows with ``.added == True`` are skipped.
            game_id:     Append to an existing worldcup (mutually exclusive with ``create``).
            create:      Dict with keys title/description/category_id (used when game_id is None).
            start_time:  Clip start in seconds applied to every selection.
            end_time:    Clip end in seconds (0 = full video).
            on_progress: Called after each track; args: (event, index, total).
        """
        if game_id is None and create is None:
            raise ConfigError("import_tracks requires either game_id or create.")

        created = False
        slug: Optional[str] = None

        if game_id is None:
            assert create is not None
            info = self.create_game(
                title=create["title"],
                description=create["description"],
                category_id=create["category_id"],
            )
            game_id = info.id
            slug = info.slug
            created = True
            logger.info("Created game id=%d slug=%s", game_id, slug)

        added = skipped = failed = 0
        total = len(tracks)

        for i, link in enumerate(tracks):
            if link.added:
                skipped += 1
                if on_progress:
                    on_progress("skipped", i, total)
                continue

            try:
                self.add_video(game_id, link.url, start_time, end_time)
                link.added = True
                added += 1
                if on_progress:
                    on_progress("added", i, total)
            except VideoAddError as exc:
                failed += 1
                logger.warning("Failed to add video %s: %s", link.url, exc)
                if on_progress:
                    on_progress("error", i, total)

        return ImportResult(
            game_id=game_id,
            slug=slug,
            created=created,
            added=added,
            skipped=skipped,
            failed=failed,
        )

    # ------------------------------------------------------------------ #
    # Internal HTTP layer
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._base_url + path
        last_exc: Exception = RuntimeError("no attempts")

        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.request(method, url, **kwargs)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    self._sleep(self._backoff(attempt))
                    continue
                raise

            if resp.ok:
                if resp.status_code == 204:
                    return None
                return resp.json()

            if resp.status_code in _RETRYABLE and attempt < self._max_retries:
                retry_after = self._parse_retry_after(resp)
                self._sleep(retry_after if retry_after else self._backoff(attempt))
                continue

            try:
                body = resp.json()
                msg = body.get("message") or str(body)
            except Exception:
                msg = resp.text or resp.reason or "unknown error"

            raise UwufufuAPIError(resp.status_code, msg)

        raise last_exc  # type: ignore[misc]

    def _backoff(self, attempt: int) -> float:
        import random
        base = self._retry_base_delay * (2 ** attempt)
        return base + random.random() * self._retry_base_delay

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> Optional[float]:
        header = resp.headers.get("Retry-After")
        if not header:
            return None
        try:
            return float(header)
        except ValueError:
            return None
