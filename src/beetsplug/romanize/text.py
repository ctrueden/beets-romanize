# This is free and unencumbered software released into the public domain.
# See https://unlicense.org/ for details.

"""Latin forms of names and titles.

In order, romanizing applies:

1. The `romanize: overrides:` table from the beets config, mapping original
   text to its Latin form, anywhere in the text. Use these to fix anything
   that comes out wrong.
2. For names: Latin artist names from MusicBrainz (see aliases.py).
   For titles: Latin titles from MusicBrainz pseudo-releases, stored by the
   plugin as `title_transl` and `album_transl` (see titles.py and
   latin_field()).
3. Readable ASCII for symbols that unidecode drops or mangles: ♥ -> (heart),
   ☆☆ -> (stars), ・ -> ., ℗ -> (P), etc.
4. Romanization of remaining Japanese with cutlet (see japanese.py).

Anything else non-ASCII is left for beets' `asciify_paths` (unidecode).
"""

import re

from confuse import ConfigError

from . import aliases, japanese
from .scripts import is_latin, kanji_is_japanese

# Transliterations applied before beets' asciify_paths (unidecode), for
# characters where unidecode's choice is unreadable or drops the character.
# Mostly letterlike symbols (U+2100-U+214F), mapped to what they look like.
_TRANSLIT = str.maketrans(
    {
        "・": ".",  # KATAKANA MIDDLE DOT (unidecode: '*')
        "∀": "A",  # FOR ALL, e.g. BRE∀K (unidecode: '')
        "Æ": "AE",
        "æ": "ae",
        "℀": "a/c",  # ACCOUNT OF
        "℁": "a/s",  # ADDRESSED TO THE SUBJECT
        "℄": "CL",  # CENTRE LINE SYMBOL
        "℅": "c/o",  # CARE OF
        "℆": "c/u",  # CADA UNA
        "ℇ": "E",  # EULER CONSTANT
        "℉": "degF",
        "℃": "degC",
        "ℏ": "h",  # PLANCK CONSTANT OVER TWO PI
        "℔": "lb",  # L B BAR SYMBOL
        "№": "No.",  # NUMERO SIGN (unidecode: 'No. ')
        "℗": "(P)",  # SOUND RECORDING COPYRIGHT
        "℘": "P",  # SCRIPT CAPITAL P
        "℞": "Rx",  # PRESCRIPTION TAKE
        "℟": "R",  # RESPONSE
        "℠": "(SM)",  # SERVICE MARK
        "℡": "(TEL)",  # TELEPHONE SIGN
        "™": "(TM)",  # TRADE MARK SIGN
        "℣": "V",  # VERSICLE
        "℥": "oz",  # OUNCE SIGN
        "Ω": "O",  # OHM SIGN (unidecode: 'ohm')
        "℧": "U",  # INVERTED OHM SIGN
        "℩": "i",  # TURNED GREEK SMALL LETTER IOTA
        "Å": "A",  # ANGSTROM SIGN
        "ℵ": "N",  # ALEF SYMBOL
        "ℶ": "b",  # BET SYMBOL
        "ℷ": "g",  # GIMEL SYMBOL
        "ℸ": "d",  # DALET SYMBOL
        "℺": "Q",  # ROTATED CAPITAL Q
        "℻": "(FAX)",  # FACSIMILE SIGN
        "ℼ": "pi",  # DOUBLE-STRUCK SMALL PI
        "ℽ": "y",  # DOUBLE-STRUCK SMALL GAMMA
        "ℾ": "G",  # DOUBLE-STRUCK CAPITAL GAMMA
        "ℿ": "P",  # DOUBLE-STRUCK CAPITAL PI
        "⅀": "E",  # DOUBLE-STRUCK N-ARY SUMMATION
        "⅁": "G",  # TURNED SANS-SERIF CAPITAL G
        "⅂": "L",  # TURNED SANS-SERIF CAPITAL L
        "⅃": "L",  # REVERSED SANS-SERIF CAPITAL L
        "⅄": "Y",  # TURNED SANS-SERIF CAPITAL Y
        "⅊": "PL",  # PROPERTY LINE
        "⅋": "&",  # TURNED AMPERSAND
        "⅌": "per",  # PER SIGN
        # Other symbols
        "☺": "(smiley)",
        "∞": "(inf)",
        "♂": "(male)",
        "♀": "(female)",
        "⚥": "(intersex)",
        "⚣": "(gay)",
        "⚢": "(lesbian)",
        "⚤": "(hetero)",
        "⚧": "(trans)",
        "⚨": "(trans)",
        "⚦": "(trans)",
        "⚩": "(trans)",
        "🜬": "(non-binary)",
        "⚲": "(neuter)",
        "☄": "(comet)",
        "☿": "(mercury)",
        "⚪": "(circle)",
        # Punctuation
        "〜": "~",  # WAVE DASH (unidecode: '~ ')
        "【": "[(",
        "】": ")]",  # (unidecode: ')] ')
        "「": "[",  # CJK quotation brackets (unidecode: '[' and '] ')
        "」": "]",
        "『": "[",
        "』": "]",
        "。": ".",  # IDEOGRAPHIC FULL STOP (unidecode: '. ')
        "•": ".",  # BULLET (unidecode: '*')
        "·": ".",  # MIDDLE DOT (unidecode: '*')
        "･": ".",  # HALFWIDTH KATAKANA MIDDLE DOT (unidecode: '*')
        "\ufe0e": "",  # VARIATION SELECTOR-15 (text style), e.g. after ⚧ or ⚪
        "\ufe0f": "",  # VARIATION SELECTOR-16 (emoji style)
    }
)

# Symbols spelled out as words, pluralized when repeated: ♥ -> (heart),
# ♥♡♥ -> (hearts). Variation selectors between repeats are tolerated.
_WORD_SYMBOLS = [
    ("♥♡", "heart", "hearts"),
    ("☆★", "star", "stars"),
    ("♪", "note", "notes"),
]
_WORD_PATTERNS = [
    (
        re.compile(f"(?:[{chars}][\ufe0e\ufe0f]?){{2,}}"),
        f"({plural})",
        re.compile(f"[{chars}]"),
        f"({single})",
    )
    for chars, single, plural in _WORD_SYMBOLS
]


_overrides = None


def reset():
    """Forget the loaded overrides, e.g. after the config changes."""
    global _overrides
    _overrides = None


def override(s):
    """Apply the `romanize: overrides:` table from the beets config.

    Overrides map original text (e.g. 矢井田瞳) to its Latin form (Hitomi
    Yaida), anywhere in s. Longer keys take precedence over shorter ones they
    contain.
    """
    global _overrides
    if _overrides is None:
        try:
            from beets import config

            table = config["romanize"]["overrides"].get(dict) or {}
        except ConfigError:
            table = {}
        table = {str(k): str(v) for k, v in table.items()}
        keys = sorted(table, key=len, reverse=True)
        _overrides = (
            (re.compile("|".join(map(re.escape, keys))), table) if keys else False
        )
    if not _overrides or not s:
        return s
    pattern, table = _overrides
    return pattern.sub(lambda m: table[m.group()], s)


def symbols(s):
    """Replace symbols with readable ASCII: ♥ -> (heart), ♥♥ -> (hearts)."""
    for many, plural, one, single in _WORD_PATTERNS:
        s = many.sub(plural, s)
        s = one.sub(single, s)
    return s.translate(_TRANSLIT)


def romanize(s, obj=None, name=False):
    """A Latin form of a title (or other text): overrides, symbols, romaji.

    `obj` is the beets Item or Album the text belongs to, if any; its
    `script` and `language` decide whether kanji are read as Japanese. With
    `name`, every romanized word is capitalized, as for a name.
    """
    if not s:
        return s
    s = symbols(override(s))
    return japanese.romanize(s, kanji=kanji_is_japanese(obj), title=name)


def romanize_name(s, obj=None):
    """A Latin form of an artist (or other) name.

    Prefers, in order: overrides, Latin names from MusicBrainz, and automatic
    romanization with every word capitalized.
    """
    if not s:
        return s
    s = override(s)
    if not is_latin(s):
        s = aliases.lookup(s) or s
    return romanize(s, obj, name=True)


def latin_field(obj, key, transl_key):
    """A field's value, or its Latin form from a pseudo-release if not Latin.

    E.g. latin_field(item, "title", "title_transl"). Overrides still take
    precedence when they make the value Latin. The result may still need
    romanize() (e.g. if there is no pseudo-release).
    """
    s = obj.get(key)
    if s and not is_latin(override(s)):
        s = obj.get(transl_key) or s
    return s
