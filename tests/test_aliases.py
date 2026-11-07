# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import pytest

from beetsplug.romanize import aliases

YAIDA = {
    "name": "矢井田瞳",
    "sort-name": "Yaida, Hitomi",
    "aliases": [
        {"name": "Yaiko", "locale": None, "type": "Search hint"},
        {"name": "Hitomi Yaida", "locale": "en", "primary": True},
        {"name": "Yaida Hitomi", "locale": "ja-Latn"},
    ],
}
KOIKE = {"name": "小池令", "sort-name": "Koike, Ryo", "aliases": []}


@pytest.fixture(autouse=True)
def names(monkeypatch):
    table = {}
    monkeypatch.setattr(aliases, "_names", table)
    monkeypatch.setattr(aliases, "_locales", lambda: ["en"])
    return table


def test_latin_name_prefers_locale():
    assert aliases.latin_name(YAIDA) == "Hitomi Yaida"
    assert aliases.latin_name(YAIDA, ["ja-Latn"]) == "Yaida Hitomi"
    # Without a preferred locale, a -Latn locale beats a search hint.
    assert aliases.latin_name(YAIDA, ["de"]) == "Yaida Hitomi"


def test_latin_name_falls_back_to_sort_name():
    assert aliases.latin_name(KOIKE) == "Ryo Koike"
    assert aliases.latin_name({"name": "誰か", "sort-name": "誰か"}) is None


def test_record_credit(names):
    credit = [
        {"artist": YAIDA, "name": "矢井田瞳", "joinphrase": " & "},
        {"artist": KOIKE, "name": "小池令"},
    ]
    aliases.record(credit, "矢井田瞳 & 小池令", "矢井田 & 小池令")
    assert names["矢井田瞳"] == "Hitomi Yaida"
    assert names["小池令"] == "Ryo Koike"
    assert names["矢井田瞳 & 小池令"] == "Hitomi Yaida & Ryo Koike"
    # An edited credit gets the individual names substituted where possible.
    assert names["矢井田 & 小池令"] == "矢井田 & Ryo Koike"


def test_record_lone_artist_under_another_name(names):
    artist = dict(YAIDA, aliases=YAIDA["aliases"] + [{"name": "やいこ"}])
    aliases.record([{"artist": artist, "name": "矢井田瞳"}], "やいこ", "ヤイコ")
    assert names["やいこ"] == "Hitomi Yaida"  # a known alias of the artist
    assert names["ヤイコ"] is None  # not a known name; nothing to substitute


def test_record_unknown(names):
    aliases.record([{"artist": {"name": "誰か", "sort-name": "誰か"}}], "誰か")
    assert names["誰か"] is None
    assert aliases.known("誰か")
    assert aliases.lookup("誰か") is None
