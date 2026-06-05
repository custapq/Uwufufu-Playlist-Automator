"""tests/test_models.py — Unit tests for data models."""

from src.models import Credentials, GameConfig, Track, UserInput, YoutubeLink


class TestTrack:
    def test_search_query(self):
        track = Track(name="ดาว", artist="Palmy")
        assert track.search_query == "ดาว Palmy"

    def test_str(self):
        track = Track(name="Shape of You", artist="Ed Sheeran")
        assert str(track) == "Shape of You - Ed Sheeran"


class TestYoutubeLink:
    def test_is_valid_with_url(self):
        link = YoutubeLink(
            track=Track(name="Test", artist="Artist"),
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        assert link.is_valid is True

    def test_is_valid_without_url(self):
        link = YoutubeLink(track=Track(name="Test", artist="Artist"))
        assert link.is_valid is False

    def test_title(self):
        link = YoutubeLink(track=Track(name="Bohemian Rhapsody", artist="Queen"))
        assert link.title == "Bohemian Rhapsody - Queen"

    def test_added_defaults_false(self):
        link = YoutubeLink(track=Track(name="Test", artist="Artist"))
        assert link.added is False


class TestGameConfig:
    def test_fields(self):
        game = GameConfig(title="My Quiz", description="Best songs")
        assert game.title == "My Quiz"
        assert game.description == "Best songs"


class TestCredentials:
    def test_fields(self):
        creds = Credentials(email="a@b.com", password="secret")
        assert creds.email == "a@b.com"
        assert creds.password == "secret"


class TestUserInput:
    def test_bundle(self):
        ui = UserInput(
            spotify_url="https://open.spotify.com/playlist/abc",
            credentials=Credentials(email="a@b.com", password="secret"),
            game=GameConfig(title="T", description="D"),
        )
        assert ui.spotify_url.endswith("abc")
        assert ui.credentials.email == "a@b.com"
        assert ui.game.title == "T"
