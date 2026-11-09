# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import pytest

from beetsplug.romanize import aliases, japanese, text
from beetsplug.romanize.scripts import is_latin, kanji_is_japanese

needs_cutlet = pytest.mark.skipif(
    not japanese.available(), reason="cutlet is not installed"
)


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from beets import config

    config.clear()
    config["romanize"]["overrides"] = {
        "矢井田瞳": "Hitomi Yaida",
        "満-MITSURU-": "MITSURU",
    }
    text.reset()
    monkeypatch.setattr(aliases, "_names", {"天野月子": "Tsukiko Amano"})
    yield config
    text.reset()


def test_is_latin():
    assert is_latin("Blue Flow (off vocal)")
    assert is_latin("Hoʻaikāne")  # modifier letter ʻokina
    assert is_latin("★ 123 !?")  # no letters at all
    assert not is_latin("硝子の夢")
    assert not is_latin("LOVE☆トロピカ〜ナ")
    assert not is_latin("Глюк’oZa")


def test_kanji_is_japanese():
    assert kanji_is_japanese(None)
    assert kanji_is_japanese({"script": "Jpan", "language": "jpn"})
    assert kanji_is_japanese({"script": "Latn", "language": "eng"})
    assert not kanji_is_japanese({"script": "Hant"})
    assert not kanji_is_japanese({"language": "zho"})


def test_symbols():
    assert text.symbols("LOVE☆Tropicana") == "LOVE(star)Tropicana"
    assert text.symbols("I ♥♡♥ you") == "I (hearts) you"
    assert text.symbols("No.1・℗2002") == "No.1.(P)2002"
    assert text.symbols("「Hi」") == "[Hi]"


def test_override():
    assert text.override("矢井田瞳") == "Hitomi Yaida"
    # Longer keys win over shorter ones they contain.
    assert text.override("満-MITSURU- live") == "MITSURU live"
    assert text.override("unrelated") == "unrelated"


def test_romanize_name_prefers_override_then_alias():
    assert text.romanize_name("矢井田瞳") == "Hitomi Yaida"
    assert text.romanize_name("天野月子") == "Tsukiko Amano"
    assert text.romanize_name("Already Latin") == "Already Latin"


def test_romanize_name_known_credit_with_override(monkeypatch, config):
    config["romanize"]["overrides"] = {
        "天道あかね": "Akane Tendo",
        "村井聖夜": "Murai Seiya",
        "星野奏子": "Kanako Hoshino",
    }
    text.reset()
    monkeypatch.setattr(
        aliases,
        "_names",
        {
            # A whole credit known from MusicBrainz, containing an override key.
            "シャンプー, 天道あかね": "Shampoo, Akane Tendō",
            "天道あかね": "Akane Tendō",
            # Known, but with a bad Latin name for the override key.
            "村井聖夜": "seiya-murai",
            "村井聖夜 meets eimy": "seiya-murai meets eimy",
            # A partly Latin credit, with the key itself left.
            "SHINE feat. 星野奏子": "SHINE feat. H",
            "星野奏子": "H",
            # A credit learned when her Latin name was different.
            "DJ X feat. 星野奏子": "DJ X feat. Q",
        },
    )
    # The credit's MusicBrainz names are kept, and the override applied.
    assert text.romanize_name("シャンプー, 天道あかね") == "Shampoo, Akane Tendo"
    assert text.romanize_name("村井聖夜") == "Murai Seiya"
    assert text.romanize_name("村井聖夜 meets eimy") == "Murai Seiya meets eimy"
    # "H" is replaced as a whole word only, not inside SHINE.
    assert text.romanize_name("SHINE feat. 星野奏子") == "SHINE feat. Kanako Hoshino"
    # If the override's Latin form cannot be placed in the known credit, the
    # overrides apply to the original credit instead.
    assert text.romanize_name("DJ X feat. 星野奏子") == "DJ X feat. Kanako Hoshino"
    # Unknown credits get the overrides, then romanization.
    assert text.romanize_name("村井聖夜 & 誰か").startswith("Murai Seiya & ")


def test_latin_field():
    item = {"title": "硝子の夢", "title_transl": "Dream of Glass"}
    assert text.latin_field(item, "title", "title_transl") == "Dream of Glass"
    # Latin values are kept, even when a Latin form is stored.
    item = {"title": "Blue Flow", "title_transl": "Something Else"}
    assert text.latin_field(item, "title", "title_transl") == "Blue Flow"
    # Overrides that make the value Latin take precedence.
    item = {"title": "矢井田瞳", "title_transl": "Hitomi Yaida's Song"}
    assert text.latin_field(item, "title", "title_transl") == "矢井田瞳"
    assert text.latin_field({"title": "夢"}, "title", "title_transl") == "夢"


@needs_cutlet
def test_romanize_japanese():
    assert text.romanize("この誰もいない部屋で") == "Kono dare mo inai heya de"
    # Romaji is separated from adjacent Latin letters.
    assert text.romanize("LOVEマシーン") == "LOVE mashiin"
    # Names capitalize every word.
    assert text.romanize_name("天野月") == "Amano Tsuki"


@needs_cutlet
def test_romanize_leaves_chinese_kanji():
    chinese = {"script": "Hant", "language": "zho"}
    assert text.romanize("趙季平", chinese) == "趙季平"
