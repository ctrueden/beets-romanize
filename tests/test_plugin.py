# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import copy
from typing import ClassVar

import pytest
from beets.test.helper import PluginTestHelper

from beetsplug import romanize
from beetsplug.romanize import aliases, japanese, musicbrainz, titles

from .test_titles import OFFICIAL, PSEUDOS

MBID = "fced703c-f4bf-47ed-9b2d-57dc8a6596e8"


@pytest.fixture
def fake_mb(monkeypatch):
    requests = []

    def get(entity, mbid, inc="", retries=4):
        requests.append((entity, mbid))
        if mbid == MBID:
            return OFFICIAL
        return PSEUDOS[mbid]

    monkeypatch.setattr(musicbrainz, "get", get)
    return requests


class TestRomanizePlugin(PluginTestHelper):
    plugin: ClassVar[str] = "romanize"

    def _album(self):
        items = [
            self.add_item(
                title=title,
                album="ブルー・フロウ",
                albumartist="Heart of Air",
                artist="Heart of Air",
                mb_albumid=MBID,
                mb_releasetrackid=f"t{i}",
                disc=1,
                track=i,
            )
            for i, title in enumerate(["Blue Flow", "硝子の夢", "蒼い祈り"], 1)
        ]
        return self.lib.add_album(items)

    def test_fetch_titles(self, fake_mb):
        album = self._album()
        self.run_command("romanize")
        album.load()
        assert album[romanize.CHECKED] == "english"
        assert "album_transl" in album  # ブルー・フロウ -> Blue Flow
        assert album["album_transl"] == "Blue Flow"
        titles_by_track = {i.track: i.get("title_transl") for i in album.items()}
        assert titles_by_track == {1: None, 2: "Dream of Glass", 3: "Aoi Inori"}

        # Already checked: not looked up again, unless forced.
        fake_mb.clear()
        self.run_command("romanize")
        assert fake_mb == []
        self.run_command("romanize", "-f")
        assert fake_mb

    def test_template_fields(self, fake_mb):
        album = self._album()
        self.run_command("romanize")
        item = next(i for i in album.items() if i.track == 2)
        assert item.evaluate_template("$title_latin") == "Dream of Glass"
        assert item.evaluate_template("$album_latin") == "Blue Flow"
        album.load()
        assert album.evaluate_template("$album_latin") == "Blue Flow"
        assert item.evaluate_template("$albumartist_latin") == "Heart of Air"

    def test_prefer_transliteration(self, fake_mb):
        self.config["romanize"]["prefer"] = titles.TRANSLITERATION
        self.unload_plugins()
        self.load_plugins()
        album = self._album()
        self.run_command("romanize")
        titles_by_track = {i.track: i.get("title_transl") for i in album.items()}
        assert titles_by_track[2] == "Glass no Yume"

    def test_no_pseudo_release(self, monkeypatch):
        monkeypatch.setattr(musicbrainz, "get", lambda *a, **k: {"relations": []})
        album = self._album()
        kept = next(i for i in album.items() if i.track == 3)
        kept["title_transl"] = "Aoi Inori"  # e.g. from mbpseudo
        kept.store()
        self.run_command("romanize")
        album.load()
        assert album[romanize.CHECKED] == "none"
        titles_by_track = {i.track: i.get("title_transl") for i in album.items()}
        assert titles_by_track == {1: None, 2: None, 3: "Aoi Inori"}

    def test_log_reports_what_was_stored(self, fake_mb, caplog):
        self._album()
        with caplog.at_level("INFO", logger="beets.romanize"):
            self.run_command("romanize")
        assert (
            "Heart of Air - ブルー・フロウ -> "
            "Blue Flow, 2/3 track titles (eng translation)"
        ) in caplog.messages

    def test_skips_latin_and_non_musicbrainz(self, fake_mb):
        self.add_item(title="Latin", album="Latin", mb_albumid=MBID)
        self.add_item(title="硝子の夢", album="x", mb_albumid="2805751")  # Discogs
        self.run_command("romanize")
        assert fake_mb == []

    def test_artist_names(self, monkeypatch):
        monkeypatch.setattr(aliases, "_names", {"矢井田瞳": "Hitomi Yaida"})
        item = self.add_item(title="t", artist="矢井田瞳", albumartist="矢井田瞳")
        assert item.evaluate_template("$artist_latin") == "Hitomi Yaida"

    def test_template_functions(self):
        self.config["romanize"]["overrides"] = {"矢井田瞳": "Hitomi Yaida"}
        romanize.text.reset()
        item = self.add_item(title="t")
        assert item.evaluate_template("%romanize_name{矢井田瞳}") == "Hitomi Yaida"
        assert item.evaluate_template("%romanize{I ♥ you}") == "I (heart) you"

    @pytest.mark.skipif(not japanese.available(), reason="cutlet is not installed")
    def test_romanization_fallback(self):
        item = self.add_item(title="この誰もいない部屋で")
        assert item.evaluate_template("$title_latin") == "Kono dare mo inai heya de"

    def test_other_fields(self):
        monkey = {"梶浦由記": "Yuki Kajiura"}
        aliases._names = monkey
        item = self.add_item(
            title="t", composers=["梶浦由記", "Nobuo Uematsu"], label="満-MITSURU-"
        )
        self.config["romanize"]["overrides"] = {"満-MITSURU-": "MITSURU"}
        romanize.text.reset()
        assert item.evaluate_template("$composers_latin") == (
            "Yuki Kajiura; Nobuo Uematsu"
        )
        assert item.evaluate_template("$label_latin") == "MITSURU"
        aliases.reset()

    def test_fetch_disc_titles(self, monkeypatch):
        official = copy.deepcopy(OFFICIAL)
        official["media"][0]["title"] = "第一部"
        pseudos = copy.deepcopy(PSEUDOS)
        pseudos["romaji"]["media"][0]["title"] = "Dai Ichibu"
        monkeypatch.setattr(
            musicbrainz,
            "get",
            lambda entity, mbid, inc="", retries=4: (
                official if mbid == MBID else pseudos[mbid]
            ),
        )
        album = self._album()
        for item in album.items():
            item.disctitle = "第一部"
            item.store()
        self.run_command("romanize")
        for item in album.items():
            assert item["disctitle_transl"] == "Dai Ichibu"
            assert item.evaluate_template("$disctitle_latin") == "Dai Ichibu"
