"""tests/test_file_manager.py — Unit tests for saving/loading YouTube links."""

import json

from src.file_manager import load_youtube_links, mark_video_added, save_youtube_links
from src.models import Track, YoutubeLink


def _sample_links():
    return [
        YoutubeLink(Track("Shape of You", "Ed Sheeran"), url="https://youtu.be/JGwWNGJdvx8"),
        YoutubeLink(Track("ดาว", "Palmy"), url=None),
    ]


class TestSaveLoadRoundtrip:
    def test_roundtrip_preserves_data(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        loaded = load_youtube_links(str(tmp_path / "out.json"))

        assert len(loaded) == 2
        assert loaded[0].track.name == "Shape of You"
        assert loaded[0].url == "https://youtu.be/JGwWNGJdvx8"
        assert loaded[1].url is None

    def test_creates_both_txt_and_json(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        assert (tmp_path / "out.json").exists()
        assert (tmp_path / "out.txt").exists()

    def test_thai_encoding_preserved(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        loaded = load_youtube_links(str(tmp_path / "out.json"))
        assert loaded[1].track.name == "ดาว"
        assert loaded[1].track.artist == "Palmy"

        # Raw JSON should contain the Thai characters, not escaped \u sequences
        raw = (tmp_path / "out.json").read_text(encoding="utf-8")
        assert "ดาว" in raw

    def test_txt_shows_no_video_found(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        txt = (tmp_path / "out.txt").read_text(encoding="utf-8")
        assert "No video found" in txt
        assert "https://youtu.be/JGwWNGJdvx8" in txt


class TestAddedFlag:
    def test_added_defaults_false_on_save(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
        assert all(item["added_to_uwufufu"] is False for item in data)

    def test_added_flag_roundtrips(self, tmp_path):
        links = _sample_links()
        links[0].added = True
        save_youtube_links(links, str(tmp_path), "out")
        loaded = load_youtube_links(str(tmp_path / "out.json"))
        assert loaded[0].added is True
        assert loaded[1].added is False


class TestMarkVideoAdded:
    def test_marks_only_matching_track(self, tmp_path):
        save_youtube_links(_sample_links(), str(tmp_path), "out")
        json_path = str(tmp_path / "out.json")

        mark_video_added(json_path, "Shape of You", "Ed Sheeran")

        data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
        marked = {item["track_name"]: item["added_to_uwufufu"] for item in data}
        assert marked["Shape of You"] is True
        assert marked["ดาว"] is False
