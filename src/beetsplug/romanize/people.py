# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Latin names for composers, lyricists, arrangers and remixers.

beets takes these from the MusicBrainz relationships of a release's
recordings and works, as the related artists' names. To find their Latin
names, the plugin looks up each person's artist ID (from the item's
`composers_ids` and so on, or else from the release's relationships), then
their aliases, and records the result in the same table as artist names (see
aliases.py), keyed by the name beets stores.
"""

from . import aliases, musicbrainz
from .scripts import is_latin

# Item fields holding people's names, and their MusicBrainz artist IDs. The
# single-valued fields are for beets before 2.9.
FIELDS = {
    "composers": "composers_ids",
    "lyricists": "lyricists_ids",
    "arrangers": "arrangers_ids",
    "remixers": "remixers_ids",
    "composer": None,
    "lyricist": None,
    "arranger": None,
    "remixer": None,
}

# The relationships beets reads these from.
RELEASE_INC = "recordings recording-level-rels work-level-rels artist-rels work-rels"
RECORDING_INC = "artist-rels work-rels work-level-rels"


def names(item):
    """The non-Latin people's names of an item."""
    found = set()
    for key in FIELDS:
        value = item.get(key)
        for name in value if isinstance(value, list) else [value]:
            if name and not is_latin(name):
                found.add(name)
    return found


def item_ids(item):
    """Map an item's people's names to their artist IDs, where beets has them."""
    ids = {}
    for key, ids_key in FIELDS.items():
        if ids_key and item.get(ids_key):
            ids.update(zip(item.get(key) or [], item.get(ids_key)))
    return ids


def relation_ids(data):
    """Map the names of all artists related to a release or recording (as
    beets stores them) to their artist IDs, from MusicBrainz data including
    relationships."""
    ids = {}

    def walk(node):
        if isinstance(node, dict):
            for rel in node.get("relations") or []:
                artist = rel.get("artist")
                if artist and artist.get("id"):
                    ids.setdefault(artist["name"], artist["id"])
                    credit = rel.get("target-credit")
                    if credit:
                        ids.setdefault(credit, artist["id"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return ids


def match(names, ids):
    """Map names to artist IDs from `ids`, ignoring spaces: names written
    with a space between family and given name (植松 伸夫, as some sources
    write them) match MusicBrainz's (植松伸夫)."""
    by_key = {_key(name): artist_id for name, artist_id in ids.items()}
    matched = {}
    for name in names:
        artist_id = ids.get(name) or by_key.get(_key(name))
        if artist_id:
            matched[name] = artist_id
    return matched


def _key(name):
    return "".join(name.split())  # Also removes ideographic spaces.


def lookup(entity, mbid):
    """Fetch a release or recording with the relationships naming people."""
    inc = RELEASE_INC if entity == "release" else RECORDING_INC
    return relation_ids(musicbrainz.get(entity, mbid, inc=inc))


def learn(name, artist_id, cache):
    """Look up an artist's Latin name, and record it for `name`.

    `cache` maps artist IDs to Latin names already looked up in this run.
    Returns the Latin name, or None if there is none.
    """
    if artist_id not in cache:
        artist = musicbrainz.get("artist", artist_id, inc="aliases")
        cache[artist_id] = aliases.latin_name(artist)
    latin = cache[artist_id]
    aliases.remember(name, latin)
    return latin
