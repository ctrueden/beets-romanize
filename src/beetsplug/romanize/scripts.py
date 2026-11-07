# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Writing-system checks."""

import unicodedata

# Scripts and languages (as tagged by MusicBrainz) whose Han characters are
# not Japanese. Objects with other or missing values are assumed Japanese,
# because script and language metadata is often missing or wrong (e.g.
# Latn/eng for a Japanese soundtrack).
NON_JAPANESE_SCRIPTS = {"Hans", "Hant", "Hani", "Kore", "Hang"}
NON_JAPANESE_LANGUAGES = {"zho", "chi", "cmn", "yue", "kor"}


def is_latin(s):
    """Whether every letter of s is Latin script (so needs no romanizing)."""
    # Modifier letters (e.g. the Hawaiian ʻokina in Hoʻaikāne) are fine too.
    return all(
        not ch.isalpha()
        or unicodedata.name(ch, "").startswith("LATIN")
        or unicodedata.category(ch) == "Lm"
        for ch in s
    )


def kanji_is_japanese(obj):
    """Whether Han characters in obj's text should be read as Japanese.

    `obj` is a beets Item or Album (or a dict, or None).
    """
    if obj is None:
        return True
    return (
        obj.get("script") not in NON_JAPANESE_SCRIPTS
        and obj.get("language") not in NON_JAPANESE_LANGUAGES
    )
