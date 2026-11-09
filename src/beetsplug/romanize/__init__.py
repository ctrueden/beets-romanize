# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Latin-script names and titles for beets paths.

`beet romanize [QUERY]` looks up, for the matching items:

- Latin names for every non-Latin artist and album artist credit not already
  known, from MusicBrainz aliases (see aliases.py).
- Latin album, disc and track titles from MusicBrainz pseudo-releases, for
  releases with non-Latin titles not already looked up (see titles.py), into
  the flexible attributes `album_transl`, `disctitle_transl` and
  `title_transl`.

`-f` looks everything up again. With `auto` (the default), newly imported
music is looked up during import, before its files are moved.

Path formats then use the `_latin` fields (`$title_latin`, `$artist_latin`,
`$composer_latin`...; see fields.py), or the template functions
`%romanize{text}` and `%romanize_name{text}` (see text.py).
"""

import requests
from beets import ui
from beets.plugins import BeetsPlugin

from . import aliases, fields, musicbrainz, text, titles
from .scripts import is_latin

# Errors from a MusicBrainz lookup: network trouble or unexpected data.
_LOOKUP_ERRORS = (requests.RequestException, ValueError, KeyError, TypeError)

# Flexible attribute recording which pseudo-release was used ('none' if the
# release has none), so that releases are not looked up again.
CHECKED = "transl_release"


class RomanizePlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add(
            {
                "auto": True,
                "titles": True,
                "languages": ["eng"],
                "prefer": titles.TRANSLATION,
                "overrides": {},
                "foreign_spelling": False,
            }
        )
        self.prefer = self.config["prefer"].as_choice(
            [titles.TRANSLATION, titles.TRANSLITERATION]
        )
        self.languages = self.config["languages"].as_str_seq()
        aliases.reset()
        text.reset()

        if self.config["auto"].get(bool):
            # A plugin stage runs after the music is added to the library and
            # before its files are moved, so paths use the Latin forms.
            self.import_stages = [self.import_stage]

        # A `_latin` field for each romanized field, e.g. $title_latin.
        for field in fields.FIELDS.values():
            func = _latin_func(field)
            self.template_fields[f"{field.key}_latin"] = func
            if field.album:
                self.album_template_fields[f"{field.key}_latin"] = func
        self.template_funcs.update(
            {
                "romanize": text.romanize,
                "romanize_name": text.romanize_name,
            }
        )

    def commands(self):
        cmd = ui.Subcommand(
            "romanize",
            help="fetch Latin-script names and titles from MusicBrainz",
        )
        cmd.parser.add_option(
            "-f",
            "--force",
            action="store_true",
            help="look up names and titles again, even if already known",
        )

        def func(lib, opts, args):
            items = list(lib.items(args))
            self.fetch_names(items, force=opts.force, verbose=True)
            if self.config["titles"].get(bool):
                self.fetch_titles(items, force=opts.force, verbose=True)

        cmd.func = func
        return [cmd]

    def import_stage(self, session, task):
        if task.skip:
            return
        items = task.imported_items()
        self.fetch_names(items)
        if self.config["titles"].get(bool):
            self.fetch_titles(items)

    ### Artist names ###

    def fetch_names(self, items, force=False, verbose=False):
        seen = set()
        fetched = learned = 0
        for item in items:
            for entity, mbid, credit in (
                ("recording", item.mb_trackid, item.artist),
                ("release", item.mb_albumid, item.albumartist),
            ):
                if not credit or is_latin(credit) or credit in seen:
                    continue
                seen.add(credit)
                if aliases.known(credit) and not force:
                    continue
                if not musicbrainz.is_mbid(mbid):
                    continue
                try:
                    learned += aliases.learn(entity, mbid, credit)
                except _LOOKUP_ERRORS as e:
                    self._log.warning("{} {}: {}", entity, mbid, e)
                    continue
                fetched += 1
                if verbose:
                    latin = aliases.lookup(credit)
                    self._log.info("{} -> {}", credit, latin or "(no Latin name)")
                if fetched % 20 == 0:
                    aliases.save()
        if fetched:
            aliases.save()
        if verbose:
            self._log.info(
                "Fetched {} credits; learned {} artist names.", fetched, learned
            )

    ### Titles ###

    def fetch_titles(self, items, force=False, verbose=False):
        # Group items by album (or by release, for singletons).
        groups = {}
        for item in items:
            key = (
                ("album", item.album_id)
                if item.album_id
                else ("release", item.mb_albumid)
            )
            groups.setdefault(key, []).append(item)

        looked_up = found = 0
        for (kind, _), group in groups.items():
            album = group[0].get_album() if kind == "album" else None
            if album is not None:
                group = list(album.items())
            mbid = group[0].mb_albumid
            album_title = album.album if album else group[0].album
            if not musicbrainz.is_mbid(mbid):
                continue
            if is_latin(album_title or "") and all(
                is_latin(item.title or "") and is_latin(item.disctitle or "")
                for item in group
            ):
                continue  # Nothing to romanize.
            holder = album if album is not None else group[0]
            if holder.get(CHECKED) and not force:
                continue
            try:
                result = titles.lookup(mbid, self.languages, self.prefer)
            except _LOOKUP_ERRORS as e:
                self._log.warning("release {}: {}", mbid, e)
                continue
            looked_up += 1
            if result:
                found += 1
            album_latin, discs, tracks = store_titles(album, group, result)
            if verbose:
                name = f"{group[0].albumartist} - {album_title}"
                if not result:
                    self._log.info("{} -> (no pseudo-release)", name)
                    continue
                found_titles = [album_latin] if album_latin else []
                if discs:
                    found_titles.append(f"{discs} disc titles")
                if tracks:
                    found_titles.append(f"{tracks}/{len(group)} track titles")
                self._log.info(
                    "{} -> {} ({} {})",
                    name,
                    ", ".join(found_titles) or "(nothing new)",
                    result["language"],
                    result["kind"],
                )
        if verbose:
            self._log.info(
                "Looked up {} releases; {} with Latin titles.", looked_up, found
            )


def store_titles(album, items, result):
    """Store a titles.lookup() result (or None) on an album and its items.

    Latin titles found are stored; existing ones (e.g. from mbpseudo) are
    kept where none is found. Returns the Latin album title stored (or None),
    and the numbers of Latin disc and track titles stored.
    """
    release = result["release"] if result else "none"
    album_latin, tracks = None, 0
    discs = set()
    if album is not None:
        album[CHECKED] = release
        album_latin = _set(
            album, "album_transl", album.album, result and result["album"]
        )
        album.store(inherit=False)
    for item in items:
        if album is None:
            item[CHECKED] = release
            album_latin = _set(
                item, "album_transl", item.album, result and result["album"]
            )
        if _set(
            item,
            "title_transl",
            item.title,
            result and titles.track_title(result, item),
        ):
            tracks += 1
        if _set(
            item,
            "disctitle_transl",
            item.disctitle,
            result and titles.disc_title(result, item),
        ):
            discs.add(item.disc or 1)
        item.store()
    return album_latin, len(discs), tracks


def _set(obj, key, original, latin):
    """Store the Latin form of a non-Latin original, if found; return it."""
    if not original or is_latin(original) or not latin:
        return None
    obj[key] = latin
    return latin


### Template fields ###


def _latin_func(field):
    if field.multi:
        # As beets formats lists: "a; b".
        return lambda obj: "; ".join(fields.latin(obj, field.key))
    return lambda obj: fields.latin(obj, field.key)
