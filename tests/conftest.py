"""Shared pytest fixtures and helpers for the v3.0.0 API-based test suite."""

from unittest.mock import MagicMock, patch

import pytest
import requests


def make_response(json_data=None, *, status: int = 200, text: str = "") -> MagicMock:
    """Build a fake ``requests.Response``.

    ``.json()`` returns ``json_data``; ``.raise_for_status()`` raises a
    ``requests.HTTPError`` (with this response attached) when ``status >= 400``,
    mirroring the real requests behaviour.
    """
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.ok = status < 400
    resp.headers = {}
    resp.text = text if text else (str(json_data) if json_data is not None else "")
    resp.json.return_value = json_data if json_data is not None else {}

    def _raise_for_status():
        if status >= 400:
            raise requests.HTTPError(f"{status} Error", response=resp)

    resp.raise_for_status.side_effect = _raise_for_status
    return resp


def http_error(status: int, text: str = "") -> requests.HTTPError:
    """Build a ``requests.HTTPError`` whose ``.response`` carries ``status``/``text``."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = text
    return requests.HTTPError(f"{status} Error", response=resp)


@pytest.fixture
def mock_response():
    """Expose :func:`make_response` as a fixture for convenience."""
    return make_response


@pytest.fixture(autouse=True)
def _no_sleep():
    """Patch ``time.sleep`` globally so retry/backoff delays don't slow the suite."""
    with patch("time.sleep", return_value=None):
        yield


@pytest.fixture(autouse=True)
def _no_dotenv_file():
    """Stop ``load_dotenv()`` from reading a developer's real ``.env`` into os.environ.

    Without this, a real ``.env`` leaks into the patched environment and breaks the
    "no credentials" tests. Keeps env-loading tests dependent only on what each test sets.
    """
    with patch("src.config.load_dotenv", return_value=False):
        yield
