# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import os
import shutil
from pathlib import Path
from typing import ClassVar

import pytest
from beets.library import Item
from beets.test.helper import PluginTestHelper
from mediafile import MediaFile

from beetsplug.romanize import aliases, fields, tags

RSRC = Path(__file__).parent / "rsrc"
FORMATS = sorted(p.name for p in RSRC.iterdir())  # min.mp3, min.flac...

NAMES = {"矢井田瞳": "Hitomi Yaida", "梶浦由記": "Yuki Kajiura"}


@pytest.fixture(autouse=True)
def names(monkeypatch):
    monkeypatch.setattr(aliases, "_names", dict(NAMES))


@pytest.fixture(autouse=True)
def restore_mediafile():
    yield
    tags.read_originals(False)


class TestTagMode(PluginTestHelper):
    plugin: ClassVar[str] = "romanize"

    def tag_mode(self, enabled):
        self.config["romanize"]["tags"] = enabled
        self.unload_plugins()
        self.load_plugins()
        aliases._names = dict(NAMES)  # Loading the plugin resets them.

    def _item(self, fixture="min.mp3"):
        path = self.temp_path / f"track-{fixture}"
        shutil.copy(RSRC / fixture, path)
        item = Item.from_path(path)
        item.update(
            {
                "title": "硝子の夢",
                "title_transl": "Glass no Yume",  # as if from a pseudo-release
                "artist": "矢井田瞳",
                "album": "Blue Flow",
                "composers": ["梶浦由記", "Nobuo Uematsu"],
            }
        )
        self.lib.add(item)
        return item

    @staticmethod
    def _raw(item):
        """The file's tags as stored, ignoring *_ORIGINAL tags."""
        mediafile = MediaFile(item.path)
        return {
            key: tags.read_raw(mediafile, key)
            for key in ("title", "artist", "album", "composers")
        } | {
            key: getattr(mediafile, key)
            for key in ("title_original", "artist_original", "album_original")
        }

    @pytest.mark.parametrize("fixture", FORMATS)
    def test_write(self, fixture):
        self.tag_mode(True)
        item = self._item(fixture)
        item.write()
        assert self._raw(item) == {
            "title": "Glass no Yume",
            "artist": "Hitomi Yaida",
            "album": "Blue Flow",
            "composers": ["Yuki Kajiura", "Nobuo Uematsu"],
            "title_original": "硝子の夢",
            "artist_original": "矢井田瞳",
            "album_original": None,  # Already Latin.
        }
        assert MediaFile(item.path).composers_original == ["梶浦由記", "Nobuo Uematsu"]

        # beets reads the originals back.
        clean = Item.from_path(item.path)
        assert clean.title == "硝子の夢"
        assert clean.artist == "矢井田瞳"
        assert clean.composers == ["梶浦由記", "Nobuo Uematsu"]
        assert "title_original" not in clean

    def test_beet_write_sees_no_changes(self):
        self.tag_mode(True)
        item = self._item()
        item.try_sync(write=True, move=False)
        mtime = os.stat(item.path).st_mtime_ns
        self.run_command("write")
        assert os.stat(item.path).st_mtime_ns == mtime

    def test_beet_update_keeps_originals(self):
        self.tag_mode(True)
        item = self._item()
        item.try_sync(write=True, move=False)
        # As if the file were changed by another program.
        os.utime(item.path, (item.mtime + 10, item.mtime + 10))
        self.run_command("update")
        item.load()
        assert item.title == "硝子の夢"
        assert item.composers == ["梶浦由記", "Nobuo Uematsu"]

    def test_tag_mode_off_restores_originals(self):
        self.tag_mode(True)
        item = self._item()
        item.try_sync(write=True, move=False)
        self.tag_mode(False)
        self.run_command("write")
        raw = self._raw(item)
        assert raw["title"] == "硝子の夢"
        assert raw["composers"] == ["梶浦由記", "Nobuo Uematsu"]
        assert raw["title_original"] is None
        assert raw["artist_original"] is None

    def test_sync(self, caplog):
        item = self._item()
        item.try_sync(write=True, move=False)  # Written without tag mode.
        self.tag_mode(True)
        # NB: Not caplog.at_level(logger=...): beets requires plugin loggers
        # to have no level of their own when it calls their listeners.
        self.run_command("romanize", "-p")
        assert self._raw(item)["title"] == "硝子の夢"  # Pretend: unchanged.
        self.run_command("romanize")
        assert self._raw(item)["title"] == "Glass no Yume"
        self.run_command("romanize")
        assert [m for m in caplog.messages if "files." in m] == [
            "Would write 1 files.",
            "Wrote 1 files.",
            "Wrote 0 files.",
        ]

        # A changed override changes what tag mode writes.
        self.config["romanize"]["overrides"] = {"硝子の夢": "Glass Dream"}
        self.tag_mode(True)
        self.run_command("romanize")
        assert self._raw(item)["title"] == "Glass Dream"


def test_write_tags_romanizes_other_values():
    # A value from another plugin (not the item's) is romanized as it is.
    item = {"title": "硝子の夢", "title_transl": "Glass no Yume"}
    written = {"title": "LOVE☆"}
    tags.write_tags(item, written, enabled=True)
    assert written == {"title": "LOVE(star)", "title_original": "LOVE☆"}


def test_keys_are_media_fields():
    keys = tags.keys()
    assert "title" in keys and "composers" in keys
    assert "work" not in keys  # Not written to files by beets.
    assert all(k in fields.FIELDS for k in keys)
