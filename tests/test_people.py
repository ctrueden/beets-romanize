# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

from typing import ClassVar

import pytest
from beets.test.helper import PluginTestHelper

from beetsplug import romanize
from beetsplug.romanize import aliases, musicbrainz, people

MBID = "fced703c-f4bf-47ed-9b2d-57dc8a6596e8"
KAJIURA = "aaaaaaaa-0000-0000-0000-000000000001"
YAMABUKI = "aaaaaaaa-0000-0000-0000-000000000002"
NOBODY = "aaaaaaaa-0000-0000-0000-000000000003"


def _rel(rel_type, artist_id, name, credit=""):
    return {
        "type": rel_type,
        "target-type": "artist",
        "target-credit": credit,
        "artist": {"id": artist_id, "name": name, "sort-name": name},
    }


# A release with recording-level (arranger) and work-level (composer,
# lyricist) relationships, as beets reads them.
RELEASE = {
    "id": MBID,
    "media": [
        {
            "tracks": [
                {
                    "recording": {
                        "relations": [
                            _rel("arranger", NOBODY, "名無し"),
                            {
                                "type": "performance",
                                "target-type": "work",
                                "work": {
                                    "relations": [
                                        _rel("composer", KAJIURA, "梶浦由記"),
                                        _rel(
                                            "lyricist",
                                            YAMABUKI,
                                            "山吹理々子",
                                            credit="RIRIKO",
                                        ),
                                    ]
                                },
                            },
                        ]
                    }
                }
            ]
        }
    ],
}

ARTISTS = {
    KAJIURA: {
        "name": "梶浦由記",
        "sort-name": "Kajiura, Yuki",
        "aliases": [{"name": "Yuki Kajiura", "locale": "en", "primary": True}],
    },
    YAMABUKI: {"name": "山吹理々子", "sort-name": "Yamabuki, Ririko", "aliases": []},
    NOBODY: {"name": "名無し", "sort-name": "名無し", "aliases": []},
}


def test_relation_ids():
    assert people.relation_ids(RELEASE) == {
        "名無し": NOBODY,
        "梶浦由記": KAJIURA,
        "山吹理々子": YAMABUKI,
        "RIRIKO": YAMABUKI,  # The credited name too.
    }


def test_names_and_item_ids():
    item = {
        "composers": ["梶浦由記", "Nobuo Uematsu"],
        "composers_ids": [KAJIURA, "x"],
        "lyricists": ["山吹理々子"],
    }
    assert people.names(item) == {"梶浦由記", "山吹理々子"}
    assert people.item_ids(item) == {"梶浦由記": KAJIURA, "Nobuo Uematsu": "x"}


def test_match_ignores_spaces():
    ids = {"梶浦由記": KAJIURA, "名無し": NOBODY}
    assert people.match({"梶浦 由記", "梶浦\u3000由記", "名無し", "x"}, ids) == {
        "梶浦 由記": KAJIURA,
        "梶浦\u3000由記": KAJIURA,
        "名無し": NOBODY,
    }


@pytest.fixture
def fake_mb(monkeypatch):
    requests = []

    def get(entity, mbid, inc="", retries=4):
        requests.append((entity, mbid))
        return RELEASE if entity == "release" else ARTISTS[mbid]

    monkeypatch.setattr(musicbrainz, "get", get)
    return requests


class TestPeople(PluginTestHelper):
    plugin: ClassVar[str] = "romanize"

    def _album(self, **values):
        item = self.add_item(
            title="t",
            album="a",
            mb_albumid=MBID,
            composers=["梶浦由記"],
            lyricists=["山吹理々子"],
            arrangers=["名無し", "Unknown To MusicBrainz 未知"],
            **values,
        )
        return self.lib.add_album([item])

    def test_fetch_people(self, fake_mb):
        aliases._names = {}
        album = self._album()
        self.run_command("romanize")
        assert aliases.names() == {
            "梶浦由記": "Yuki Kajiura",  # An English alias.
            "山吹理々子": "Ririko Yamabuki",  # The sort name.
            "名無し": None,  # No Latin name.
        }
        album.load()
        assert album[romanize.PEOPLE_CHECKED] == MBID
        item = album.items().get()
        assert item.evaluate_template("$composers_latin") == "Yuki Kajiura"
        assert item.evaluate_template("$lyricists_latin") == "Ririko Yamabuki"

        # Each artist's aliases are looked up once; the release is not looked
        # up again, even for the name it lacks, unless forced.
        assert fake_mb.count(("artist", KAJIURA)) == 1
        fake_mb.clear()
        self.run_command("romanize")
        assert fake_mb == []
        self.run_command("romanize", "-f")
        assert ("release", MBID) in fake_mb

    def test_item_ids_avoid_release_lookup(self, fake_mb):
        aliases._names = {}
        self.add_item(
            title="t",
            mb_albumid=MBID,
            composers=["梶浦由記"],
            composers_ids=[KAJIURA],
        )
        self.run_command("romanize")
        assert ("release", MBID) not in fake_mb
        assert aliases.lookup("梶浦由記") == "Yuki Kajiura"

    def test_disabled(self, fake_mb):
        self.config["romanize"]["people"] = False
        self.unload_plugins()
        self.load_plugins()
        aliases._names = {}
        self._album()
        self.run_command("romanize")
        assert ("release", MBID) not in fake_mb
