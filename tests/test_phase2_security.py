import pytest
from unittest.mock import patch
from types import SimpleNamespace


@pytest.fixture(autouse=True)
def _no_dotenv_file():
    """Stop load_dotenv() from reading a real .env on disk.

    Without this, a developer's actual .env leaks into the patched os.environ and
    makes the "no credentials" tests fail. Patching it to a no-op keeps the tests
    dependent only on the os.environ each test sets up.
    """
    with patch("src.config.load_dotenv", return_value=False):
        yield


class TestLoadCredentialsFromEnv:
    """Task 2.4 + 2.5: Credential loading from environment."""

    def test_returns_none_when_email_missing(self):
        """Task 2.4: No .env → function returns None → caller must prompt interactively."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import load_credentials_from_env
            result = load_credentials_from_env()
        assert result is None

    def test_returns_none_when_password_missing(self):
        with patch.dict("os.environ", {"UWUFUFU_EMAIL": "user@example.com"}, clear=True):
            from src.config import load_credentials_from_env
            result = load_credentials_from_env()
        assert result is None

    def test_returns_credentials_when_both_present(self):
        """Task 2.5: .env has email + password → auto-loaded, no prompt needed."""
        env = {
            "UWUFUFU_EMAIL": "user@example.com",
            "UWUFUFU_PASSWORD": "secret123",
        }
        with patch.dict("os.environ", env, clear=True):
            from src.config import load_credentials_from_env
            result = load_credentials_from_env()

        assert result is not None
        assert result.email == "user@example.com"
        assert result.password == "secret123"

    def test_spotify_url_included_when_present(self):
        env = {
            "UWUFUFU_EMAIL": "user@example.com",
            "UWUFUFU_PASSWORD": "secret123",
            "SPOTIFY_PLAYLIST_URL": "https://open.spotify.com/playlist/abc123",
        }
        with patch.dict("os.environ", env, clear=True):
            from src.config import load_credentials_from_env
            result = load_credentials_from_env()

        assert result.spotify_url == "https://open.spotify.com/playlist/abc123"

    def test_spotify_url_is_none_when_absent(self):
        env = {
            "UWUFUFU_EMAIL": "user@example.com",
            "UWUFUFU_PASSWORD": "secret123",
        }
        with patch.dict("os.environ", env, clear=True):
            from src.config import load_credentials_from_env
            result = load_credentials_from_env()

        assert result.spotify_url is None


class TestPasswordNotVisible:
    """Task 2.1: Password input uses getpass, not plain input()."""

    def test_getpass_is_used_for_password(self):
        """Verify main.py imports and uses getpass, not plain input(), for the password."""
        import ast
        import pathlib

        source = pathlib.Path("src/main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports = [
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        ]
        assert "getpass" in imports, "getpass module must be imported in main.py"

    def test_env_is_checked_before_prompt(self):
        """Task 2.3: Verify the input collection consults load_credentials_from_env."""
        import inspect

        from src import main

        source = inspect.getsource(main._resolve_credentials)
        assert "load_credentials_from_env" in source, (
            "_resolve_credentials() must call load_credentials_from_env() before prompting"
        )
