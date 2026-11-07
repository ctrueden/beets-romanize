# beets-romanize

[![License](https://img.shields.io/pypi/l/beets-romanize.svg)](https://github.com/ctrueden/beets-romanize/raw/main/UNLICENSE)
[![PyPI](https://img.shields.io/pypi/v/beets-romanize.svg)](https://pypi.org/project/beets-romanize)
[![Python Version](https://img.shields.io/pypi/pyversions/beets-romanize.svg)](https://python.org)

A [beets](https://beets.io) plugin that gives your music Latin-script paths,
while leaving the tags in their original scripts.

beets' `asciify_paths` option uses
[unidecode](https://pypi.org/project/Unidecode/), which converts one character
at a time and reads every kanji with its Mandarin reading:
この誰もいない部屋で becomes `konoShui moinaiBu Wu de`. Romanizing reliably is
not possible in general: 一日 reads *ichinichi* or *tsuitachi* depending on
meaning, names have irregular readings, and artists invent their own (see
[beets#1916](https://github.com/beetbox/beets/issues/1916)). So this plugin
looks up what people have already written down before it guesses:

| Step | Source | Example |
|---|---|---|
| 1 | Your `overrides` table | 満-MITSURU- → `MITSURU` |
| 2 | Names: MusicBrainz artist aliases and sort names | 矢井田瞳 → `Hitomi Yaida` |
| 2 | Titles: MusicBrainz [pseudo-releases](https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases) | 硝子の夢 → `Dream of Glass` or `Glass no Yume` |
| 3 | Readable ASCII for symbols unidecode drops or mangles | LOVE☆ → `LOVE(star)`, ♥♥ → `(hearts)` |
| 4 | Japanese romanization in context, with [cutlet](https://github.com/polm/cutlet) | この誰もいない部屋で → `Kono dare mo inai heya de` |

Anything else non-ASCII (e.g. Korean, Cyrillic) is left for `asciify_paths`.

## Setup

1. Install the plugin into the same environment as beets. For Japanese
   romanization (step 4), include the `japanese` extra, which installs cutlet
   and a dictionary of about 50 MB:
   ```
   pip install "beets-romanize[japanese]"
   ```

2. Add `romanize` to the `plugins:` section of your beets config.

3. Use the plugin's fields in your path formats, for example:
   ```yaml
   asciify_paths: yes
   paths:
     default: $albumartist_latin/$album_latin%aunique{}/$track $title_latin
     singleton: Non-Album/$artist_latin/$title_latin
     comp: Compilations/$album_latin%aunique{}/$track $artist_latin - $title_latin
   ```

4. Look up Latin names and titles for music you already have, then move the
   files to their new paths (check with `beet move -p` first):
   ```
   beet romanize
   beet move
   ```
   New imports are looked up automatically, before their files are moved.

## Path fields and functions

| Field | For | Value |
|---|---|---|
| `$title_latin` | items | Latin form of the title |
| `$artist_latin` | items | Latin form of the artist |
| `$album_latin` | items, albums | Latin form of the album title |
| `$albumartist_latin` | items, albums | Latin form of the album artist |

The template functions `%romanize{text}` and `%romanize_name{text}` romanize
any other value (e.g. `%romanize_name{$composer}`). They apply the overrides,
known artist names, symbols and romanization, but not pseudo-release titles,
which belong to a particular item or album. Names capitalize every romanized
word (`Amano Tsuki`); titles capitalize only the first (`Kono dare mo...`).

Kanji are read as Japanese unless the item's `script` or `language` is Chinese
or Korean. To fix a misread release, set those fields, e.g.
`beet modify -a album:… script=Hant language=zho`.

## The `romanize` command

`beet romanize [QUERY]` looks up, for the matching items:

- **Artist names:** Latin names for every non-Latin artist and album artist
  credit, from the MusicBrainz aliases of the credited artists. Aliases in the
  locales of beets' `import.languages` are preferred (English if that is
  empty), then any `-Latn` locale, then the artist's Latin sort name
  (`Yaida, Hitomi` → `Hitomi Yaida`).
- **Titles:** for releases with non-Latin album or track titles, Latin titles
  from their pseudo-releases.

Use `-f` to look up again what is already known.

Only music matched to MusicBrainz (with an `mb_albumid` or `mb_trackid`) can
be looked up; everything else gets only the overrides, symbols and
romanization.

## Configuration

Defaults shown:

```yaml
romanize:
  auto: yes              # look up newly imported music
  titles: yes            # look up pseudo-release titles
  languages: [eng]       # translation languages, most preferred first
  prefer: translation    # or: transliteration
  foreign_spelling: no   # cutlet: モノクロレター -> "Monochrome letter"
  overrides: {}          # original text -> Latin form
```

### Translation or transliteration?

A release can have several Latin-script pseudo-releases: say, an English
translation (`Dream of Glass`) and a romaji transliteration (`Glass no Yume`).
A pseudo-release counts as a *translation* if its language is in `languages`
(ISO 639-3 codes, as MusicBrainz uses: `eng`, `deu`, `fra`...), and as a
*transliteration* if its language is that of the original release.
Pseudo-releases in other languages are ignored. `prefer` picks which kind
wins. Each title comes from the most preferred pseudo-release that has a
Latin form of it, so an incomplete translation is filled in from the
transliteration.

### Overrides

Overrides map original text to its Latin form, anywhere in a name or title,
and take precedence over everything else. Longer keys win over shorter ones
they contain. Use them to fix anything that comes out wrong:

```yaml
romanize:
  overrides:
    早乙女乱馬: Ranma Saotome
    シャープネル: Sharpnel
```

### Foreign spelling

With `foreign_spelling`, cutlet restores the original spelling of katakana
loanwords (モノクロレター → `Monochrome letter` rather than `Monokuro
retaa`). That is often nicer, but sometimes wrong: シャープネル (DJ Sharpnel)
becomes `sharp flannel`.

## Where the data is kept

Lookups are kept, so that paths stay the same until you ask otherwise:

- **Artist names** go in `romanize-names.json` in the beets config directory,
  keyed by the artist credit as beets stores it. It is regenerated by
  `beet romanize`, but treat it like a lockfile rather than a cache: if
  MusicBrainz changes in the meantime, regenerating it can rename folders.
- **Titles** go in the beets database, as flexible attributes:
  `title_transl` (items) and `album_transl` (albums) hold the Latin titles,
  and `transl_release` (albums, or singleton items) the MBID of the
  pseudo-release used, or `none` if there is none. The first two have the same
  names as in beets' `mbpseudo` plugin. They are not written to the files'
  tags. Existing values (e.g. from `mbpseudo`) are kept unless a Latin title
  is found to replace them.

## Related

- beets' built-in [`mbpseudo`](https://beets.readthedocs.io/en/stable/plugins/mbpseudo.html)
  plugin can import pseudo-release data directly, as tags or in place of the
  original metadata. This plugin instead keeps the original tags and uses
  pseudo-releases only for paths, with per-language preferences, and it works
  for music already in the library.

## Development

```
make test   # run the tests
make lint   # format and lint
make dist   # build release archives
```

These need [uv](https://docs.astral.sh/uv/).
