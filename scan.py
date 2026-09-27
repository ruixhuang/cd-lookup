#!/usr/bin/env python3
"""Build docs/index.json from the album folder names on the music share.

Standard library only. Walks two levels below the root (genre / album) plus one
extra level for box sets, and never descends into album contents.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

RE_CATALOG = re.compile(r"^\[(.+?)\]\s*-\s*")
RE_LEAD_YEAR = re.compile(r"^(\d{4})\s*-\s*")
RE_TRAIL_YEAR = re.compile(r"\s*\((\d{4})\)\s*$")
RE_MID_YEAR = re.compile(r"^(\d{4})\s*-\s*")
SEP = " - "

# Names with these extensions are files; skipping them avoids a network stat per track.
RE_FILE_EXT = re.compile(
    r"\.(flac|m4a|mp3|wav|aiff?|ape|wv|ogg|opus|aac|alac|dsf|dff|dts|iso|mka|"
    r"cue|log|txt|nfo|sfv|md5|m3u8?|pls|accurip|"
    r"jpe?g|png|gif|bmp|tiff?|webp|pdf|db|ini|url|torrent|zip|rar|7z)$", re.I)


RE_MOJIBAKE = re.compile(r"[\u00c2\u00c3][\u0080-\u00bf]")


def fix_mojibake(s):
    """Repair UTF-8 text that was mis-decoded as Latin-1 ("AndrÃ¡s" -> "András").

    macOS stores names in decomposed form (NFD), so compose first or the
    tell-tale "Ã" is invisible to the regex.
    """
    s = unicodedata.normalize("NFC", s)
    if not RE_MOJIBAKE.search(s):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_name(name):
    """Split a folder name into artist / title / year / catalog.

    Rules, in order:
      1. leading "[CATALOG] - "
      2. leading "1986 - " or "1986-"
      3. trailing " (1971)"
      4. leading "- " marks a compilation with no artist
      5. split on the first " - "
      6. a year right after the artist ("Artist - 1962 - Title")
    """
    rest = fix_mojibake(name).strip()
    catalog = year = None

    m = RE_CATALOG.match(rest)
    if m:
        catalog = m.group(1).strip()
        rest = rest[m.end():]

    m = RE_LEAD_YEAR.match(rest)
    if m:
        year = int(m.group(1))
        rest = rest[m.end():]

    m = RE_TRAIL_YEAR.search(rest)
    if m:
        year = year or int(m.group(1))
        rest = rest[: m.start()]

    rest = rest.strip()
    if rest.startswith("- "):
        return {"artist": "", "title": rest[2:].strip(), "year": year, "catalog": catalog}

    if SEP in rest:
        artist, title = rest.split(SEP, 1)
        artist, title = artist.strip(), title.strip()
        m = RE_MID_YEAR.match(title)
        if m and year is None and len(title) > m.end():
            year = int(m.group(1))
            title = title[m.end():].strip()
    else:
        artist, title = "", rest

    return {"artist": artist, "title": title, "year": year, "catalog": catalog}


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["exclude"] = set(cfg.get("exclude", []))
    cfg["child_skip"] = [re.compile(p, re.I) for p in cfg.get("child_skip_patterns", [])]
    return cfg


def subdirs(path):
    """Yield (name, fullpath) for real, non-hidden subdirectories."""
    try:
        with os.scandir(path) as it:
            for e in sorted(it, key=lambda e: e.name):
                if e.name.startswith(".") or e.name.startswith("@") or RE_FILE_EXT.search(e.name):
                    continue
                try:
                    if e.is_dir(follow_symlinks=False):
                        yield e.name, e.path
                except OSError:
                    continue
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)


def make_item(genre, name, relpath, parent=None):
    p = parse_name(name)
    return {
        "g": genre,
        "a": p["artist"],
        "t": p["title"],
        "y": p["year"],
        "c": p["catalog"],
        "p": relpath,
        "parent": parent,
    }


def scan(cfg, limit=None, verbose=False):
    root = cfg["root"]
    items = []
    skipped_children = 0
    for genre, gpath in subdirs(root):
        if genre in cfg["exclude"]:
            continue
        for album, apath in subdirs(gpath):
            items.append(make_item(genre, album, f"{genre}/{album}"))
            if verbose:
                print(f"  {genre}/{album}", file=sys.stderr)
            for child, _ in subdirs(apath):
                if any(rx.search(child) for rx in cfg["child_skip"]):
                    skipped_children += 1
                    continue
                items.append(make_item(genre, child, f"{genre}/{album}/{child}", parent=album))
            if limit and len(items) >= limit:
                return items, skipped_children
    items.sort(key=lambda i: i["p"])
    return items, skipped_children


def write_index(items, out_path):
    """Write the index only when the item list changed. Returns True if written."""
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                if json.load(f).get("items") == items:
                    return False
        except (OSError, ValueError):
            pass
    doc = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "items": items,
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    os.replace(tmp, out_path)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--dry-run", action="store_true", help="print parsed entries, do not write")
    ap.add_argument("--limit", type=int, help="stop after roughly N entries")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if not os.path.isdir(cfg["root"]):
        print(f"error: root not found or not mounted: {cfg['root']}", file=sys.stderr)
        return 2

    t0 = time.time()
    items, skipped = scan(cfg, limit=args.limit, verbose=args.verbose)
    elapsed = time.time() - t0

    if args.dry_run:
        for i in items:
            tag = f"  [child of: {i['parent']}]" if i["parent"] else ""
            print(f"{i['g']:>22} | {i['a'] or '-':<40.40} | {i['t']:<50.50} | {i['y'] or '':<4} | {i['c'] or ''}{tag}")
        print(f"\n{len(items)} entries, {skipped} child folders skipped, {elapsed:.1f}s", file=sys.stderr)
        return 0

    out_path = os.path.join(HERE, cfg["output"])
    written = write_index(items, out_path)
    children = sum(1 for i in items if i["parent"])
    status = "written" if written else "unchanged"
    print(f"{len(items)} entries ({children} children), {skipped} child folders skipped, "
          f"{elapsed:.1f}s, index {status}: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
