# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import pytest

from beetsplug.romanize import aliases, fields, japanese, text

needs_cutlet = pytest.mark.skipif(
    not japanese.available(), reason="cutlet is not installed"
)


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from beets import config

    config.clear()
    config["romanize"]["overrides"] = {"満-MITSURU-": "MITSURU"}
    text.reset()
    monkeypatch.setattr(
        aliases, "_names", {"矢井田瞳": "Hitomi Yaida", "梶浦由記": "Yuki Kajiura"}
    )
    yield config
    text.reset()


def test_table():
    for key, field in fields.FIELDS.items():
        assert field.key == key
        assert field.kind in (fields.NAME, fields.TITLE)
    # Lists and their single-valued forms are both covered.
    assert fields.FIELDS["composers"].multi
    assert not fields.FIELDS["composer"].multi


def test_names():
    item = {"artist": "矢井田瞳", "composer": "梶浦由記", "label": "満-MITSURU-"}
    assert fields.latin(item, "artist") == "Hitomi Yaida"
    assert fields.latin(item, "composer") == "Yuki Kajiura"
    assert fields.latin(item, "label") == "MITSURU"


def test_multi_valued():
    item = {"composers": ["梶浦由記", "Nobuo Uematsu"]}
    assert fields.latin(item, "composers") == ["Yuki Kajiura", "Nobuo Uematsu"]
    assert fields.latin({}, "composers") == []


def test_pseudo_release_titles():
    item = {"disctitle": "第一部", "disctitle_transl": "Dai Ichibu"}
    assert fields.latin(item, "disctitle") == "Dai Ichibu"
    # A Latin value is used as is, even if a Latin form was stored.
    assert fields.latin({"title": "Blue", "title_transl": "x"}, "title") == "Blue"


def test_empty():
    assert fields.latin({}, "title") is None
    assert fields.latin({"work": ""}, "work") == ""


@needs_cutlet
def test_romanization():
    assert fields.latin({"work": "この誰もいない部屋で"}, "work") == (
        "Kono dare mo inai heya de"
    )
    # Names capitalize every word.
    assert fields.latin({"lyricist": "天野月"}, "lyricist") == "Amano Tsuki"
