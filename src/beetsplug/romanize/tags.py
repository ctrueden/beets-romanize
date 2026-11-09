# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Tag mode: Latin forms in the files' tags, with the originals kept.

With `tags: yes`, the beets database keeps the original values (e.g. title
硝子の夢), and only the files get the Latin forms (TITLE=Glass no Yume), with
each original in a tag of its own (TITLE_ORIGINAL=硝子の夢). Three parts:

- Writing: a `write` event handler, which beets calls just before it writes
  a file's tags, swaps in the Latin forms and adds the *_ORIGINAL tags. With
  tag mode off, it removes any *_ORIGINAL tags instead, so `beet write`
  restores the original values.
- Reading: the fields' descriptors on beets' MediaFile class are wrapped, so
  that beets reads a field's *_ORIGINAL tag where a file has one. Then beets
  always sees the original values: `beet write` does not find the Latin
  forms to be changes (and rewrite every file each time), and `beet update`
  and imports do not read them into the database.
- Syncing: `sync()` writes the files whose tags differ from what tag mode
  would write, e.g. after turning tag mode on, or after the overrides or
  looked-up titles change. (`beet write` cannot tell, since it sees the
  original values.)
"""

import copy

from beets.library import Item
from beets.util import syspath
from mediafile import (
    ASFStorageStyle,
    ListMediaField,
    ListStorageStyle,
    MediaField,
    MediaFile,
    MP3DescStorageStyle,
    MP3ListDescStorageStyle,
    MP4ListStorageStyle,
    MP4StorageStyle,
    StorageStyle,
)

from . import fields

SUFFIX = "_original"


def original_key(key):
    """The MediaFile field for a field's original value: title_original."""
    return key + SUFFIX


def keys():
    """The romanized fields that beets writes to files."""
    media = set(MediaFile.fields())
    return [key for key in fields.FIELDS if key in Item._media_fields and key in media]


### Registering the *_ORIGINAL tags ###


def register():
    """Add a MediaFile field for each original value (once)."""
    for key in keys():
        okey = original_key(key)
        if okey in MediaFile.__dict__:
            continue
        name = okey.upper()
        if fields.FIELDS[key].multi:
            descriptor = ListMediaField(
                MP3ListDescStorageStyle(desc=name),
                MP4ListStorageStyle(f"----:com.apple.iTunes:{name}"),
                ListStorageStyle(name),
                ASFStorageStyle(name),
            )
        else:
            descriptor = MediaField(
                MP3DescStorageStyle(name),
                MP4StorageStyle(f"----:com.apple.iTunes:{name}"),
                StorageStyle(name),
                ASFStorageStyle(name),
            )
        # Not via BeetsPlugin.add_media_field: beets must not read these
        # into the database, only write them (see write_tags()).
        MediaFile.add_field(okey, descriptor)


### Reading the originals ###

_raw = {}  # field -> its original (unwrapped) MediaFile descriptor
_wrapper_classes = {}  # descriptor class -> its subclass preferring originals


def read_originals(enabled):
    """Whether beets reads each field's *_ORIGINAL tag, where a file has one."""
    for key in keys():
        raw = _raw.setdefault(key, MediaFile.__dict__[key])
        # MediaFile.add_field refuses to replace a field, so set it directly.
        setattr(MediaFile, key, _wrap(raw, key) if enabled else raw)


def _wrap(raw, key):
    cls = type(raw)
    wrapper = _wrapper_classes.get(cls)
    if wrapper is None:

        def __get__(self, mediafile, owner=None):
            if mediafile is None:
                return self
            original = getattr(mediafile, self.romanize_original)
            if original:
                return original
            return cls.__get__(self, mediafile, owner)

        wrapper = type(f"Original{cls.__name__}", (cls,), {"__get__": __get__})
        _wrapper_classes[cls] = wrapper
    wrapped = copy.copy(raw)
    wrapped.__class__ = wrapper
    wrapped.romanize_original = original_key(key)
    return wrapped


def read_raw(mediafile, key):
    """A field's value as stored in the file, ignoring *_ORIGINAL tags."""
    descriptor = _raw.get(key) or MediaFile.__dict__[key]
    return descriptor.__get__(mediafile, MediaFile)


### Writing ###


def write_tags(item, tags, enabled):
    """Swap Latin forms into a dict of tags about to be written to a file.

    `tags` maps MediaFile fields to the values beets is writing (normally the
    item's). With tag mode `enabled`, each non-Latin value is replaced by its
    Latin form and kept in the field's *_original tag; otherwise, the
    *_original tags are removed.
    """
    for key in keys():
        if key not in tags:
            continue
        okey = original_key(key)
        value = tags[key]
        latin = _latin(item, key, value) if enabled else value
        if _empty(value) or latin == value:
            tags[okey] = None  # Removes any old one from the file.
        else:
            tags[key] = latin
            tags[okey] = value


def _latin(item, key, value):
    if value == item.get(key):
        return fields.latin(item, key)  # With any looked-up Latin form.
    # Some other plugin is writing its own value: romanize that.
    field = fields.FIELDS[key]
    if field.multi:
        return [fields.latin_value(field, v, item) for v in value or []]
    return fields.latin_value(field, value, item)


def _empty(value):
    return value is None or value == "" or value == []


### Syncing ###


def expected(item, enabled):
    """The values tag mode writes to an item's file, for the romanized fields."""
    tags = {key: item.get(key) for key in keys()}
    write_tags(item, tags, enabled)
    return tags


def differences(item, enabled):
    """Fields whose values in the item's file differ from expected(): a dict
    of field -> (in the file, expected).
    """
    mediafile = MediaFile(syspath(item.path))
    diffs = {}
    for key, want in expected(item, enabled).items():
        have = (
            getattr(mediafile, key)
            if key.endswith(SUFFIX)
            else read_raw(mediafile, key)
        )
        if _empty(have) and _empty(want):
            continue
        if have != want:
            diffs[key] = (have, want)
    return diffs
