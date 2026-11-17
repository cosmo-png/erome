<h1 align="center">erome<span>-dl</span></h1>
<p align="center">Scan a profile, pick the albums you want, download them. All from the terminal.</p>

---

## Install

```bash
git clone https://github.com/cosmo-png/erome-dl.git
cd erome-dl
pip install .
```

Needs Python 3.10+.

## Use

Paste a profile link and you get a menu:

```bash
erome-dl https://www.erome.com/someuser
```

```
╭──────────── @someuser ────────────╮
│  #  Album            Photos Videos  Status   │
│  1  Beach day            12      3  ● new    │
│  2  Studio set            0      8  ✓ saved  │
│  3  Weekend trip         24      1  ● new    │
╰───── 3 shown of 3 · 2 new · 1 saved ─────────╯
Download (all · new · 1,4,7 · 3-10 · /keyword · q):
```

| Type      | Does                                          |
|-----------|-----------------------------------------------|
| `all`     | every album in the current view               |
| `new`     | only albums not downloaded before             |
| `1,4,7`   | those albums                                  |
| `3-10`    | a range                                       |
| `/beach`  | filter the list by title (numbers stay valid) |
| `q`       | quit                                          |

Then it asks for images, videos or both, and downloads with progress bars into
`downloads/<username>/<album>_<id>/`.

### Skip the menu

```bash
erome-dl <profile> --list-only        # just show the table
erome-dl <profile> --all              # grab everything
erome-dl <profile> --new-only         # only what's new since last time
erome-dl <profile> --all --videos-only
erome-dl <album-link>                 # a single album
erome-dl -f links.txt --new-only      # many links, one per line
```

### Options

| Flag | What |
|------|------|
| `-o, --output` | output folder (default `downloads`) |
| `-w, --workers` | parallel downloads (default 4) |
| `--delay` | seconds between page requests (default 0.6) |
| `--images-only` / `--videos-only` | filter by type |
| `--cookies "a=b; c=d"` | raw Cookie header if the site asks for it |
| `--proxy URL` | HTTP or SOCKS proxy |

### Config file

Defaults can live in `~/.erome-dl/config.toml`:

```toml
output  = "~/Videos/erome"
workers = 6
delay   = 0.8
proxy   = "http://127.0.0.1:8080"
```

Set `EROME_DL_HOME` to move the config and history somewhere else.

## How it behaves

- **Resume:** interrupted files continue from the `.part` file next run.
- **Size check:** each file is compared with the server's Content-Length; truncated files are discarded and retried.
- **History:** an album counts as saved once all of its selected files finish. Stored in `~/.erome-dl/history.db`.
- **Polite:** random delay between page requests, backoff on rate limits.

## If it says "No albums found" or "no media"

The scraper reads the site's HTML, so a layout change can break it. Only two functions
need touching: `parse_profile` and `parse_album` in `src/erome_dl/scraper.py`.
Open a page, view source, and adjust the selectors there.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests run offline against a fake session; CI runs them on Python 3.10 to 3.12.

## Layout

```
src/erome_dl/
  cli.py          flow + menu
  scraper.py      profile and album parsing
  downloader.py   resumable, size-checked downloads
  history.py      SQLite record of saved albums
  selection.py    "1,4,7" / "3-10" parser
  ui.py           banner, tables, progress bars
  config.py       config.toml loading
tests/
```

## Disclaimer

Only download content you have the right to save, and follow the site's terms and the laws where you live.
The `--delay` default is there to keep the load on the site small. Please leave it on.

## License

MIT
