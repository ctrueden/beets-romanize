# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

import copy

from beetsplug.romanize import titles

OFFICIAL = {
    "id": "official",
    "title": "Blue Flow",
    "text-representation": {"script": "Jpan", "language": "jpn"},
    "relations": [
        {
            "type": "transl-tracklisting",
            "direction": "forward",
            "release": {
                "id": "romaji",
                "text-representation": {"script": "Latn", "language": "jpn"},
            },
        },
        {
            "type": "transl-tracklisting",
            "direction": "forward",
            "release": {
                "id": "english",
                "text-representation": {"script": "Latn", "language": "eng"},
            },
        },
        {
            "type": "transl-tracklisting",
            "direction": "forward",
            "release": {
                "id": "french",
                "text-representation": {"script": "Latn", "language": "fra"},
            },
        },
        {
            "type": "transl-tracklisting",
            "direction": "forward",
            "release": {
                "id": "kana",
                "text-representation": {"script": "Kana", "language": "jpn"},
            },
        },
        {
            # The other direction: this release is itself a pseudo-release.
            "type": "transl-tracklisting",
            "direction": "backward",
            "release": {
                "id": "backward",
                "text-representation": {"script": "Latn", "language": "jpn"},
            },
        },
    ],
    "media": [
        {
            "position": 1,
            "tracks": [
                {"id": "t1", "position": 1, "title": "Blue Flow"},
                {"id": "t2", "position": 2, "title": "硝子の夢"},
                {"id": "t3", "position": 3, "title": "蒼い祈り"},
            ],
        }
    ],
}


def _pseudo(title, *track_titles):
    return {
        "title": title,
        "media": [
            {
                "position": 1,
                "tracks": [
                    {"position": i + 1, "title": t} for i, t in enumerate(track_titles)
                ],
            }
        ],
    }


PSEUDOS = {
    "romaji": _pseudo("Blue Flow", "Blue Flow", "Glass no Yume", "Aoi Inori"),
    # An incomplete translation: track 3 is still in Japanese.
    "english": _pseudo("Blue Flow", "Blue Flow", "Dream of Glass", "蒼い祈り"),
}


def test_candidates_prefer_translation():
    assert titles.candidates(OFFICIAL, ["eng"]) == [
        ("translation", "eng", "english"),
        ("transliteration", "jpn", "romaji"),
    ]


def test_candidates_prefer_transliteration():
    assert titles.candidates(OFFICIAL, ["eng"], titles.TRANSLITERATION) == [
        ("transliteration", "jpn", "romaji"),
        ("translation", "eng", "english"),
    ]


def test_candidates_language_order():
    assert [c[2] for c in titles.candidates(OFFICIAL, ["fra", "eng"])] == [
        "french",
        "english",
        "romaji",
    ]


def test_resolve_falls_back_per_track():
    result = titles.resolve(OFFICIAL, PSEUDOS.__getitem__, ["eng"])
    assert result["release"] == "english"
    assert result["kind"] == "translation"
    assert result["album"] == "Blue Flow"
    assert result["tracks"] == {
        "t1": "Blue Flow",
        "t2": "Dream of Glass",
        "t3": "Aoi Inori",  # from the romaji pseudo-release
    }


def test_resolve_without_candidates():
    assert titles.resolve({"relations": []}, PSEUDOS.__getitem__, ["eng"]) is None


def test_track_title():
    result = titles.resolve(OFFICIAL, PSEUDOS.__getitem__, ["eng"])
    assert titles.track_title(result, {"mb_releasetrackid": "t2"}) == "Dream of Glass"
    # Without a release track ID, fall back to the position.
    assert titles.track_title(result, {"disc": 1, "track": 3}) == "Aoi Inori"
    assert titles.track_title(result, {"disc": 2, "track": 1}) is None


def _with_disc_title(release, title):
    release = copy.deepcopy(release)
    release["media"][0]["title"] = title
    return release


def test_resolve_disc_titles():
    # Only the less preferred pseudo-release has a Latin disc title.
    official = _with_disc_title(OFFICIAL, "第一部")
    pseudos = {
        "english": _with_disc_title(PSEUDOS["english"], "第一部"),
        "romaji": _with_disc_title(PSEUDOS["romaji"], "Dai Ichibu"),
    }
    result = titles.resolve(official, pseudos.__getitem__, ["eng"])
    assert result["discs"] == {1: "Dai Ichibu"}
    assert titles.disc_title(result, {"disc": 1}) == "Dai Ichibu"
    assert titles.disc_title(result, {}) == "Dai Ichibu"  # disc 1 by default
    assert titles.disc_title(result, {"disc": 2}) is None
