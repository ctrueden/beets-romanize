# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""The beets fields the plugin romanizes, and how.

Each field is either a name (a person, group or label: Latin names from
MusicBrainz are preferred, and every romanized word is capitalized) or a title
(Latin titles from a pseudo-release are preferred, if the plugin looks them
up). Some fields hold several values, each romanized on its own.

`latin(obj, key)` gives a field's Latin form. It is computed each time, from
the field's value, the overrides, the looked-up data (artist names, and the
`*_transl` attributes from pseudo-releases) and cutlet, so it follows changes
to any of them. Only looked-up data is stored.
"""

from dataclasses import dataclass

from . import text

NAME = "name"
TITLE = "title"


@dataclass(frozen=True)
class Field:
    key: str
    kind: str  # NAME or TITLE
    multi: bool = False  # a list of values (e.g. composers)
    album: bool = False  # also an album field
    transl: str | None = None  # flexible attribute with a looked-up Latin form


FIELDS = {
    f.key: f
    for f in [
        # Titles
        Field("title", TITLE, transl="title_transl"),
        Field("album", TITLE, album=True, transl="album_transl"),
        Field("disctitle", TITLE, transl="disctitle_transl"),
        Field("work", TITLE),
        Field("grouping", TITLE),
        Field("release_group_title", TITLE, album=True),
        # Artists
        Field("artist", NAME),
        Field("artist_sort", NAME),
        Field("artist_credit", NAME),
        Field("artists", NAME, multi=True),
        Field("artists_sort", NAME, multi=True),
        Field("artists_credit", NAME, multi=True),
        Field("albumartist", NAME, album=True),
        Field("albumartist_sort", NAME, album=True),
        Field("albumartist_credit", NAME, album=True),
        Field("albumartists", NAME, multi=True, album=True),
        Field("albumartists_sort", NAME, multi=True, album=True),
        Field("albumartists_credit", NAME, multi=True, album=True),
        # Other people, and labels. Since beets 2.9, items have only the
        # lists (composers...), not the single-valued fields.
        Field("composer", NAME),
        Field("composer_sort", NAME),
        Field("composers", NAME, multi=True),
        Field("lyricist", NAME),
        Field("lyricists", NAME, multi=True),
        Field("arranger", NAME),
        Field("arrangers", NAME, multi=True),
        Field("remixer", NAME),
        Field("remixers", NAME, multi=True),
        Field("label", NAME, album=True),
    ]
}


def latin(obj, key):
    """The Latin form of a field of a beets Item or Album.

    A list for multi-valued fields; otherwise a string (or the field's value,
    e.g. None, if empty).
    """
    field = FIELDS[key]
    value = obj.get(key)
    if field.multi:
        return [latin_value(field, v, obj) for v in value or []]
    if field.transl:
        value = text.latin_field(obj, key, field.transl)
    return latin_value(field, value, obj)


def latin_value(field, value, obj=None):
    """The Latin form of one value of a field (without looked-up titles)."""
    if not value or not isinstance(value, str):
        return value
    if field.kind == NAME:
        return text.romanize_name(value, obj)
    return text.romanize(value, obj)
