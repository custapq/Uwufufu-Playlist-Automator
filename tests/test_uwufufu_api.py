from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.exceptions import GameCreationError, LoginError, VideoAddError
from src.uwufufu_api import UwufufuAPIClient, UwufufuAPIError
from tests.conftest import make_response, http_error


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _client() -> tuple[UwufufuAPIClient, MagicMock]:
    session = MagicMock(spec=requests.Session)
    session.headers = {}
    client = UwufufuAPIClient(max_retries=0, session=session)
    return client, session


def _ok(json_data: object, status: int = 200) -> MagicMock:
    return make_response(json_data, status=status)


def _err(status: int, text: str = "error") -> MagicMock:
    return make_response({"message": text}, status=status)


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

class TestLogin:
    def test_stores_token_on_success(self):
        client, session = _client()
        session.request.return_value = _ok({"accessToken": "tok123"}, status=201)

        token = client.login("a@b.com", "password1")

        assert token == "tok123"
        assert client._token == "tok123"
        assert session.headers["Authorization"] == "Bearer tok123"

    def test_raises_login_error_on_401(self):
        client, session = _client()
        session.request.return_value = _err(401, "Unauthorized")

        with pytest.raises(LoginError):
            client.login("bad@b.com", "wrongpassword")

    def test_raises_login_error_on_network_failure(self):
        client, session = _client()
        session.request.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(LoginError):
            client.login("a@b.com", "password1")

    def test_sends_correct_payload(self):
        client, session = _client()
        session.request.return_value = _ok({"accessToken": "t"}, status=201)

        client.login("user@example.com", "mypassword")

        _, kwargs = session.request.call_args
        assert kwargs["json"] == {"email": "user@example.com", "password": "mypassword"}


# ─────────────────────────────────────────────
# Games
# ─────────────────────────────────────────────

class TestCreateGame:
    def test_returns_game_info_on_success(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 42, "slug": "my-quiz"}, status=201)

        info = client.create_game("My Quiz", "desc", category_id=16)

        assert info.id == 42
        assert info.slug == "my-quiz"

    def test_raises_game_creation_error_on_api_error(self):
        client, session = _client()
        session.request.return_value = _err(500, "server error")

        with pytest.raises(GameCreationError):
            client.create_game("Quiz", "desc", category_id=16)

    def test_sends_draft_visibility(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 1, "slug": "s"}, status=201)

        client.create_game("T", "D", category_id=16)

        _, kwargs = session.request.call_args
        assert kwargs["json"]["visibility"] == "IS_CLOSED"
        assert kwargs["json"]["categoryId"] == 16


class TestPublishGame:
    def test_sends_is_public(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 7}, status=200)

        client.publish_game(7, category_id=16, locale="en")

        _, kwargs = session.request.call_args
        assert kwargs["json"]["visibility"] == "IS_PUBLIC"

    def test_raises_game_creation_error_on_failure(self):
        client, session = _client()
        session.request.return_value = _err(403, "forbidden")

        with pytest.raises(GameCreationError):
            client.publish_game(7, category_id=16)


# ─────────────────────────────────────────────
# Selections
# ─────────────────────────────────────────────

class TestAddVideo:
    def test_returns_selection_on_success(self):
        client, session = _client()
        selection = {"id": 99, "url": "https://youtube.com/watch?v=abc"}
        session.request.return_value = _ok(selection, status=201)

        result = client.add_video(42, "https://youtube.com/watch?v=abc")

        assert result["id"] == 99

    def test_sends_correct_payload(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 1}, status=201)

        client.add_video(42, "https://youtube.com/watch?v=xyz", start_time=10, end_time=60)

        _, kwargs = session.request.call_args
        assert kwargs["json"]["worldcupId"] == 42
        assert kwargs["json"]["url"] == "https://youtube.com/watch?v=xyz"
        assert kwargs["json"]["startTime"] == 10
        assert kwargs["json"]["endTime"] == 60

    def test_raises_video_add_error_on_failure(self):
        client, session = _client()
        session.request.return_value = _err(422, "invalid url")

        with pytest.raises(VideoAddError):
            client.add_video(42, "not-a-url")


# ─────────────────────────────────────────────
# Retry logic
# ─────────────────────────────────────────────

class TestRetry:
    def test_retries_on_429_then_succeeds(self):
        client, session = _client()
        client._max_retries = 2
        session.request.side_effect = [
            _err(429, "rate limited"),
            _ok({"accessToken": "tok"}, status=201),
        ]

        token = client.login("a@b.com", "password1")
        assert token == "tok"
        assert session.request.call_count == 2

    def test_raises_after_exhausting_retries(self):
        client, session = _client()
        client._max_retries = 1
        session.request.side_effect = [
            _err(500, "server error"),
            _err(500, "server error"),
        ]

        with pytest.raises(LoginError):
            client.login("a@b.com", "password1")

        assert session.request.call_count == 2

    def test_does_not_retry_on_400(self):
        client, session = _client()
        client._max_retries = 2
        session.request.return_value = _err(400, "bad request")

        with pytest.raises(LoginError):
            client.login("a@b.com", "password1")

        assert session.request.call_count == 1


# ─────────────────────────────────────────────
# import_tracks
# ─────────────────────────────────────────────

class TestImportTracks:
    def _make_link(self, url: str, added: bool = False):
        link = MagicMock()
        link.url = url
        link.added = added
        return link

    def test_creates_game_and_adds_videos(self):
        client, session = _client()
        session.request.side_effect = [
            _ok({"id": 10, "slug": "quiz"}, status=201),   # create_game
            _ok({"id": 1}, status=201),                     # add_video 1
            _ok({"id": 2}, status=201),                     # add_video 2
        ]

        links = [self._make_link("https://youtube.com/watch?v=a"),
                 self._make_link("https://youtube.com/watch?v=b")]

        result = client.import_tracks(
            links,
            create={"title": "T", "description": "D", "category_id": 16},
        )

        assert result.game_id == 10
        assert result.created is True
        assert result.added == 2
        assert result.skipped == 0
        assert result.failed == 0

    def test_skips_already_added(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 1}, status=201)

        links = [
            self._make_link("https://youtube.com/watch?v=a", added=True),
            self._make_link("https://youtube.com/watch?v=b"),
        ]

        result = client.import_tracks(links, game_id=99)

        assert result.skipped == 1
        assert result.added == 1

    def test_counts_failures_without_raising(self):
        client, session = _client()
        session.request.return_value = _err(422, "invalid")

        links = [self._make_link("https://youtube.com/watch?v=a")]

        result = client.import_tracks(links, game_id=99)

        assert result.failed == 1
        assert result.added == 0

    def test_raises_config_error_without_game_id_or_create(self):
        from src.exceptions import ConfigError
        client, session = _client()

        with pytest.raises(ConfigError):
            client.import_tracks([])

    def test_calls_on_progress(self):
        client, session = _client()
        session.request.return_value = _ok({"id": 1}, status=201)

        events: list[str] = []
        links = [self._make_link("https://youtube.com/watch?v=a")]

        client.import_tracks(links, game_id=99, on_progress=lambda e, i, t: events.append(e))

        assert events == ["added"]
