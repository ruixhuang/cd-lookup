# CD/LP Lookup

Live site: **https://ruixhuang.github.io/cd-lookup/**

A static search page for the album folders on the music share
(`/Volumes/ServerFolders/Music Rip`). A Python script builds a JSON index of the
folder names; the page searches that index in the browser. There is no server and
no build step. The only external dependency is GitHub (git hosting + Pages).

**The index is public by design.** Anyone with the URL can see the full list of
artist and album names. Paths in the index are relative to the share root, so no
machine or user details are exposed.

## Files

| Path | Purpose |
| --- | --- |
| `scan.py` | Standard-library indexer. Walks genre / album / box-set folders and writes `docs/index.json`. |
| `config.json` | Share path, excluded top-level folders, patterns for child folders to skip (e.g. `CD1`, `Scans`). |
| `update.sh` | Rebuilds the index and pushes it if anything changed. |
| `docs/index.html` | The search page. Vanilla HTML/CSS/JS, fuzzy and substring matching. |
| `docs/index.json` | Generated index. Committed so Pages can serve it. |
| `tests/test_parse.py` | Tests for the folder-name parser. |
| `tests/search_smoke.mjs` | Headless Node check of the page's search logic. |

## Refresh the index

With the share mounted:

```sh
./update.sh
```

This scans the share (a couple of minutes over SMB), rewrites `docs/index.json`
only if the folder list changed, commits, and pushes. GitHub Pages redeploys
within a minute or so.

## Local preview

```sh
python3 scan.py            # or: python3 scan.py --dry-run --limit 40
python3 -m http.server -d docs 8000
open http://localhost:8000
```

## Tests

```sh
python3 -m unittest              # folder-name parser
node tests/search_smoke.mjs      # search logic in docs/index.html (uses docs/index.json if present)
```

## GitHub Pages setup (already done)

The repo `ruixhuang/cd-lookup` is public (free Pages needs a public repo) and Pages is
configured as **Deploy from a branch**, branch `main`, folder `/docs`. To recreate it
elsewhere:

```sh
gh repo create <user>/cd-lookup --public --source=. --remote=origin --push
gh api -X POST repos/<user>/cd-lookup/pages -f 'source[branch]=main' -f 'source[path]=/docs'
```

## Folder-name rules the parser understands

- `Artist - Album`
- `[ECM 1001] - artist - album (1969)` (catalog number and year)
- `- Compilation Title` (no artist)
- `1986-Artist - Album` or `1994 - Title` (leading year)
- `Artist - 1962 - Album` (year after the artist, common in box sets)
- Anything without ` - ` is stored as a title with no artist.
