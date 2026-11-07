# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("beets-romanize")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "unknown"
