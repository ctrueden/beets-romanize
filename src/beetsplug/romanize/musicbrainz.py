# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Minimal MusicBrainz API client, respecting its rate limit."""

import re
import time

from .about import __version__

URL = "https://musicbrainz.org/ws/2"
USER_AGENT = (
    f"beets-romanize/{__version__} ( https://github.com/ctrueden/beets-romanize )"
)
INTERVAL = 1.1  # seconds between requests; MusicBrainz allows 1/s

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_last_request = 0.0


def is_mbid(s):
    """Whether s looks like a MusicBrainz ID (and not e.g. a Discogs ID)."""
    return bool(s and UUID.match(s))


def get(entity, mbid, inc="", retries=4):
    """Fetch an entity (e.g. a release) as JSON."""
    import requests

    global _last_request
    params = {"fmt": "json"}
    if inc:
        params["inc"] = inc
    for attempt in range(retries + 1):
        wait = _last_request + INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        response = requests.get(
            f"{URL}/{entity}/{mbid}",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        # MusicBrainz answers 503 when it is overloaded or we are too fast.
        if response.status_code == 503 and attempt < retries:
            time.sleep(2**attempt * 5)
            continue
        response.raise_for_status()
        return response.json()
