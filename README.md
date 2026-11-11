# beets-romanize

[![License](https://img.shields.io/pypi/l/beets-romanize.svg)](https://github.com/ctrueden/beets-romanize/raw/main/UNLICENSE)
[![PyPI](https://img.shields.io/pypi/v/beets-romanize.svg)](https://pypi.org/project/beets-romanize)
[![Python Version](https://img.shields.io/pypi/pyversions/beets-romanize.svg)](https://python.org)

A [beets](https://beets.io) plugin that gives your music Latin-script paths
(and, optionally, tags), while your beets library keeps the metadata in its
original scripts. (Unlike beets' `mbpseudo` plugin, which replaces it: see
[Related](#related).)

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

## Example outcomes

From a real library, comparing `asciify_paths` alone (unidecode), cutlet
alone, and the plugin's result.

**Transliteration from a pseudo-release.** Readings that only a person can
know, because a word has several valid readings or is stylized:

| Original             | unidecode                           | cutlet                       | beets-romanize                  |
|----------------------|-------------------------------------|------------------------------|---------------------------------|
| 明日は今日と同じ未来 | `Ming Ri haJin Ri toTong ziWei Lai` | `Asu wa kyou to onaji mirai` | `Ashita wa Kyou to Onaji Mirai` |
| 漸-ZEN               | `Jian -ZEN`                         | `Susumu-ZEN`                 | `ZEN`                           |

**Translation from a pseudo-release.** Made-up names and English titles
written in katakana:

| Original | unidecode | cutlet | beets-romanize |
|---|---|---|---|
| 灰羽連盟 サウンドトラック ハネノネ | `Hui Yu Lian Meng  saundotoratsuku hanenone` | `Haiwa renmei Saundo torakku Hane no ne` | `Haibane-Renmei Soundtrack HANENONE` |
| LOVE☆トロピカ〜ナ デラックス | `LOVEtoropika~ na deratsukusu` | `LOVE(star)Toro pika~Na Derakkusu` | `Love Tropicana Deluxe` |
| 桜蘭高校ホスト部 サントラ & キャラソン集 前編 | `Ying Lan Gao Xiao hosutoBu  santora & kiyarasonJi  Qian Bian` | `Sakura Ran koukou hosuto bu Santora & Kyarasonshuu Zenpen` | `Ouran High School Host Club Soundtrack & Character Song Collection <First Part>` |

Where a release has both kinds, `prefer` chooses: 硝子の夢 becomes
`Dream of Glass` (translation) or `Glass no Yume` (transliteration).

**Romanization with cutlet.** With no pseudo-release, cutlet reads kanji as
Japanese rather than Mandarin, and splits words:

| Original             | unidecode                 | beets-romanize              |
|----------------------|---------------------------|-----------------------------|
| この誰もいない部屋で | `konoShui moinaiBu Wu de` | `Kono dare mo inai heya de` |
| さよならを聴かせて   | `sayonarawoTing kasete`   | `Sayonara wo kikasete`      |
| 愛のカケラ           | `Ai nokakera`             | `Ai no kakera`              |

It is not perfect, though. These are better than unidecode, but still need
an override or a pseudo-release:

| Original              | unidecode            | beets-romanize          | Ideal                   |
|-----------------------|----------------------|-------------------------|-------------------------|
| ナイト・オブ・ナイツ  | `naito*obu*naitsu`   | `Naito.obu.naitsu`      | `Night of Knights`      |
| カナコのサーフィンJPN | `kanakonosa-huinJPN` | `Kana ko no saafin JPN` | `Kanako no Surfin' JPN` |
| ジェットにんぢん      | `zietsutonindin`     | `Jetto ni n ji n`       | `Jet Ninjin`            |

English written in katakana is spelled as pronounced (`foreign_spelling`
can help; see below), names can be split (カナコ, *Kanako*), and unfamiliar
spellings (にんぢん, an old spelling of にんじん, *ninjin*) are read kana by
kana.

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

Every field below has a Latin form as a `_latin` field: `$title_latin`,
`$artist_latin`, `$composers_latin` and so on.

| Kind | Fields | Latin form from |
|---|---|---|
| Titles | `title`, `album`, `disctitle` | pseudo-release, else romanization |
| | `work`, `grouping`, `release_group_title` | romanization |
| Artists | `artist`, `albumartist`, plus their `_sort` and `_credit` forms and the lists `artists`, `albumartists`, etc. | MusicBrainz artist names, else romanization |
| Other people | `composers`, `lyricists`, `arrangers`, `remixers`, `composer_sort` | MusicBrainz artist names, else romanization |
| Labels | `label` | romanization |

All of them apply the overrides and symbols first. Names capitalize every
romanized word (`Amano Tsuki`); titles capitalize only the first (`Kono dare
mo...`). Album fields (`album`, `albumartist...`, `label`,
`release_group_title`) have `_latin` fields for albums too. Lists come out as
beets shows them, e.g. `Yuki Kajiura; Nobuo Uematsu`.

The template functions `%romanize{text}` and `%romanize_name{text}` romanize
any other value, as a title or a name. They apply the overrides, known artist
names, symbols and romanization, but not pseudo-release titles, which belong
to a particular item or album.

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
- **Other people:** Latin names for non-Latin composers, lyricists, arrangers
  and remixers, the same way. Their artist IDs come from the items'
  `composers_ids` (and so on) where beets has them, or else from the
  release's relationships. Names are matched with spaces ignored, so 植松 伸夫
  (as some sources write it) matches MusicBrainz's 植松伸夫.
- **Titles:** for releases with non-Latin album, disc or track titles, Latin
  titles from their pseudo-releases.

Use `-f` to look up again what is already known.

In [tag mode](#tag-mode), `beet romanize` then writes the files whose tags are
out of date. `beet romanize -p` only lists them, and looks nothing up.

Only music matched to MusicBrainz (with an `mb_albumid` or `mb_trackid`) can
be looked up; everything else gets only the overrides, symbols and
romanization.

## Configuration

Defaults shown:

```yaml
romanize:
  auto: yes              # look up newly imported music
  titles: yes            # look up pseudo-release titles
  people: yes            # look up composers', lyricists'... names
  languages: [eng]       # translation languages, most preferred first
  prefer: translation    # or: transliteration
  foreign_spelling: no   # cutlet: モノクロレター -> "Monochrome letter"
  overrides: {}          # original text -> Latin form
  tags: no               # write Latin forms to the files' tags too
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

### Tag mode

By default, the plugin changes only paths: the beets database and your files'
tags keep the original values. With `tags: yes`, the files' tags get the
Latin forms too, so music players show them, while the database keeps the
originals:

| | Database | File tags |
|---|---|---|
| Title | `title`: 硝子の夢 | `TITLE`: Glass no Yume, `TITLE_ORIGINAL`: 硝子の夢 |
| Composers | `composers`: 梶浦由記; Nobuo Uematsu | `COMPOSER`: Yuki Kajiura; Nobuo Uematsu, `COMPOSERS_ORIGINAL`: 梶浦由記; Nobuo Uematsu |

Every romanized field that beets writes to files is covered (all those under
[Path fields and functions](#path-fields-and-functions) except `work` and
`release_group_title`). A `*_ORIGINAL` tag is added only where the Latin form
differs. These are ordinary custom tags in each format (ID3 `TXXX` frames,
Vorbis comments, MP4 freeform atoms, APEv2 and ASF attributes); players
ignore them.

Since the database keeps the originals, `beet mbsync`, re-imports and
`beet modify` work as usual, and the Latin forms are recomputed whenever a
file is written. When reading files, beets reads a field's `*_ORIGINAL` tag
where there is one, so `beet update` and imports never mistake the Latin
forms for new values, and `beet write` does not count them as changes. That
also means `beet write` cannot tell when the Latin forms in a file are out of
date, so use `beet romanize` for that:

- **Turning tag mode on:** run `beet romanize` to write the Latin forms to
  your files. `beet romanize -p` lists which files would change first.
- **After changing overrides** (or anything else that changes Latin forms):
  `beet romanize` again. It writes only files whose tags would change.
- **Turning tag mode off:** run `beet write`, which restores the original
  values and removes the `*_ORIGINAL` tags.

If another program changes a file's tags, beets still reads the
`*_ORIGINAL` values; so to change a value, change it in beets.

## Where the data is kept

Lookups are kept, so that paths stay the same until you ask otherwise:

- **Artist names** (and other people's) go in `romanize-names.json` in the
  beets config directory, keyed by the name or credit as beets stores it. It is regenerated by
  `beet romanize`, but treat it like a lockfile rather than a cache: if
  MusicBrainz changes in the meantime, regenerating it can rename folders.
- **Titles** go in the beets database as flexible attributes:
  `title_transl` and `disctitle_transl` (items) and `album_transl` (albums)
  hold the Latin titles; `transl_release` holds the MBID of the
  pseudo-release used, or `none` if there is none. `title_transl` and
  `album_transl` have the same names as in beets' `mbpseudo` plugin. They are
  not written to the files' tags (in tag mode, the Latin forms are, as
  `TITLE` and so on). Existing values (e.g. from `mbpseudo`) are kept unless a
  Latin title is found to replace them.
- **Releases whose people were looked up** are recorded in `transl_people`
  (albums, or singleton items), as the MBID of the release, so that they are
  not looked up again.

## Related

beets' built-in [`mbpseudo`](https://beets.readthedocs.io/en/stable/plugins/mbpseudo.html)
plugin also uses MusicBrainz pseudo-releases, but for a different purpose:
it *replaces* your metadata with the pseudo-release's, while beets-romanize
*keeps* your metadata and adds Latin forms alongside it.

With beets-romanize, the database still holds the original titles, so you
can still search for them, and the Latin forms are available as fields:

```
$ beet ls -a -f '$album | $album_latin' 硝子
硝子の夢 | Dream of Glass
```

With mbpseudo, if you pick the pseudo-release when importing, the album is
stored as `Dream of Glass` (or `Glass no Yume`, whichever Latin-script
pseudo-release MusicBrainz lists first), and `beet ls -a 硝子` finds
nothing: the original titles are not kept. Its `custom_tags_only` option
instead keeps the originals and adds `album_transl`, `title_transl` and
`artist_transl` fields to the database and the files' tags, but they are not
used in paths unless you write path formats around them, and they are empty
for anything without a pseudo-release.

Either way, mbpseudo takes only the album and track titles from the
pseudo-release (and, with `import.languages`, artist aliases). Labels,
composers and other people stay as on the original release, often in the
original script, and are left to `asciify_paths`.

| | mbpseudo | beets-romanize |
|---|---|---|
| Original metadata in the database | Replaced (kept with `custom_tags_only`) | Always kept |
| Latin forms in the files' tags | Always (as the main tags, or as `*_transl` tags) | Only with `tags: yes`, which keeps the originals in `*_ORIGINAL` tags; undone by `beet write` |
| When | Only while importing | While importing, or any time with `beet romanize` |
| Which pseudo-release | The first in a wanted script | By language: translation or transliteration, per `languages` and `prefer` |
| Without a pseudo-release | Nothing | Overrides, artist aliases, symbols, Japanese romanization (cutlet) |
| Fields | Album and track titles, artists | Also disc titles, composers, lyricists, arrangers, remixers, labels... |

So mbpseudo suits you if you would rather your library *were* the
pseudo-release: if you want the English or romanized release as your
metadata, and are importing music that has one. beets-romanize suits you if
the original-script metadata is what you want to keep, and you want readable
paths (and, optionally, readable tags) for all of it, including music
already in your library and music with no pseudo-release.

If you use mbpseudo to replace your metadata, beets-romanize can still fill
in what it leaves alone: labels, composers and other people, and music with
no pseudo-release. If you use its `custom_tags_only` mode, beets-romanize
reads the `title_transl` and `album_transl` fields it writes, so switching
keeps them, though beets-romanize replaces them where it finds a Latin title
itself.

## Development

```
make test   # run the tests
make lint   # format and lint
make dist   # build release archives
```

These need [uv](https://docs.astral.sh/uv/).
