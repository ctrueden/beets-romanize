# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Latin-script artist names from MusicBrainz aliases.

Romanizing a name mechanically often goes wrong: name readings are irregular
(小池令 is Ryo Koike, not "Koike Rei"), and segmentation can fail (矢井田瞳 is
Hitomi Yaida, not "Ya Ida Hitomi"). MusicBrainz knows better: most artists
have an English alias or a Latin-script sort name.

Paths cannot query MusicBrainz on the fly, so the plugin fetches Latin names
ahead of time into a JSON file in the beets config directory, keyed by the
original artist credit. The file acts like a lockfile: once a name is known,
it stays the same (and so do paths) until looked up again with `-f`.

Aliases in the locales of beets' `import.languages` are preferred (English if
that is empty), as for the musicbrainz plugin's own alias handling.
"""

import json
import os

from confuse import ConfigError

from . import musicbrainz
from .scripts import is_latin

NAMES_FILENAME = "romanize-names.json"

_names = None  # credit or name -> Latin name, or None if none is known


def _names_path():
    from beets import config

    return os.path.join(config.config_dir(), NAMES_FILENAME)


def names():
    """The table of known names, loaded on first use."""
    global _names
    if _names is None:
        try:
            with open(_names_path(), encoding="utf-8") as f:
                _names = json.load(f).get("names", {})
        except (OSError, ValueError):
            _names = {}
    return _names


def reset():
    """Forget the loaded table, e.g. after the config directory changes."""
    global _names
    _names = None


def save():
    path = _names_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"names": names()}, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def lookup(name):
    """Return the known Latin form of an artist credit or name, or None."""
    return names().get(name) if name else None


def remember(name, latin):
    """Record the Latin form of a name (None if there is none)."""
    names()[name] = latin if latin and latin != name else None


def known(name):
    """Whether name has been looked up already (even if nothing was found)."""
    return name in names()


### Choosing names ###


def _locales():
    from beets import config

    try:
        locales = config["import"]["languages"].as_str_seq()
    except ConfigError:
        locales = []
    return locales or ["en"]


def latin_name(artist, locales=None):
    """Choose a Latin-script name for a MusicBrainz artist, or None."""
    if is_latin(artist["name"]):
        return artist["name"]
    if locales is None:
        locales = _locales()

    aliases = [a for a in artist.get("aliases", []) if is_latin(a["name"])]

    def rank(alias):
        locale = alias.get("locale") or ""
        return (
            locales.index(locale) if locale in locales else len(locales),
            not locale.endswith("-Latn"),
            alias.get("type") == "Search hint",
            not alias.get("primary"),
        )

    if aliases:
        return min(aliases, key=rank)["name"]

    # Fall back to the sort name, if Latin: "Yaida, Hitomi" -> "Hitomi Yaida".
    sort_name = artist.get("sort-name") or ""
    if sort_name and is_latin(sort_name):
        last, sep, first = sort_name.partition(", ")
        return f"{first} {last}" if sep else sort_name

    return None


def _known_names(artist):
    return {artist["name"], artist.get("sort-name")} | {
        alias["name"] for alias in artist.get("aliases", [])
    }


def learn(entity, mbid, *credits):
    """Fetch a recording or release, and record Latin names for its artists.

    Returns the number of names learned. Each of `credits` (the artist credit
    strings beets stored, e.g. item.artist) is recorded too, so that it is not
    fetched again even if MusicBrainz knows no Latin form.
    """
    data = musicbrainz.get(entity, mbid, inc="artist-credits aliases")
    return record(data.get("artist-credit") or [], *credits)


def record(credit, *credits):
    """Record Latin names from a MusicBrainz artist credit; see learn()."""
    table = names()
    locales = _locales()

    learned = 0
    original, credited, latin = "", "", ""
    for part in credit:
        artist = part["artist"]
        join = part.get("joinphrase", "")
        name = latin_name(artist, locales)
        if name and not is_latin(artist["name"]):
            table[artist["name"]] = name
            learned += 1
        original += artist["name"] + join
        credited += part.get("name", artist["name"]) + join
        latin += (name or artist["name"]) + join

    # If only some of the artists have Latin names, keep the partly Latin
    # credit; the rest is romanized later.
    for key in (original, credited):
        if key and not is_latin(key):
            table[key] = latin if latin != key else None
    # A credit stored by beets may match neither form exactly (e.g. if it was
    # edited, or mixes scripts); substitute the individual artist names.
    for key in credits:
        if key and key not in table:
            if len(credit) == 1 and key in _known_names(credit[0]["artist"]):
                # A lone artist, credited under another of its names.
                latin = latin_name(credit[0]["artist"], locales) or key
            else:
                latin = key
                for part in credit:
                    name = latin_name(part["artist"], locales)
                    if name:
                        latin = latin.replace(part["artist"]["name"], name)
            table[key] = latin if latin != key else None
    return learned
