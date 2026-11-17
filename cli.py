from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.prompt import Prompt

from . import __version__, ui
from .config import load_config
from .downloader import download_album
from .history import History
from .scraper import (
    album_from_url,
    clean_name,
    is_album_url,
    load_album,
    make_session,
    profile_username,
    scan_profile,
)
from .selection import parse_selection


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="erome-dl",
        description="Scan an erome.com profile, pick albums, download them.",
    )
    p.add_argument("urls", nargs="*", help="profile or album links")
    p.add_argument("-f", "--file", help="text file with one link per line")
    p.add_argument("-o", "--output", help="output folder (default: downloads)")
    p.add_argument("-w", "--workers", type=int, help="parallel downloads (default: 4)")
    p.add_argument("--delay", type=float, help="seconds between page requests (default: 0.6)")
    pick = p.add_mutually_exclusive_group()
    pick.add_argument("--all", action="store_true", help="download every album, no menu")
    pick.add_argument("--new-only", action="store_true", help="download only albums not in history")
    pick.add_argument("--list-only", action="store_true", help="just list albums and exit")
    kind = p.add_mutually_exclusive_group()
    kind.add_argument("--images-only", action="store_true")
    kind.add_argument("--videos-only", action="store_true")
    p.add_argument("--cookies", help="raw Cookie header string, if the site needs it")
    p.add_argument("--proxy", help="e.g. http://127.0.0.1:8080 or socks5://...")
    p.add_argument("--version", action="version", version=f"erome-dl {__version__}")
    return p


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if "://" not in raw:
        raw = "https://" + raw
    host = urlparse(raw).netloc.lower()
    if host != "erome.com" and not host.endswith(".erome.com"):
        raise ValueError(f"not an erome.com link: {raw}")
    return raw


def load_details(session, albums, delay, workers, console) -> None:
    todo = [a for a in albums if not a.loaded]
    if not todo:
        return

    def work(album):
        try:
            load_album(session, album, delay)
        except Exception as exc:  # keep going; the table flags it
            album.error = str(exc)[:80]

    with ui.make_progress(console, transient=True) as progress:
        task = progress.add_task("Reading albums", total=len(todo))
        with ThreadPoolExecutor(max_workers=min(max(workers, 1), 6)) as pool:
            for fut in as_completed([pool.submit(work, a) for a in todo]):
                fut.result()
                progress.advance(task)


def choose_albums(console, albums, done_ids, title):
    view = list(range(len(albums)))
    ui.show_albums(console, albums, done_ids, view, title)
    while True:
        raw = Prompt.ask(
            "[bold]Download[/] [dim](all · new · 1,4,7 · 3-10 · /keyword · q)[/]"
        ).strip()
        low = raw.lower()
        if not raw:
            continue
        if low in ("q", "quit", "exit"):
            return []
        if raw.startswith("/"):
            kw = raw[1:].strip().lower()
            view = [i for i, a in enumerate(albums) if kw in a.title.lower()]
            if not view:
                console.print("[yellow]No titles match that.[/]")
                view = list(range(len(albums)))
            ui.show_albums(console, albums, done_ids, view, title)
            continue
        if low == "all":
            return [albums[i] for i in view if not albums[i].error]
        if low == "new":
            return [albums[i] for i in view if albums[i].id not in done_ids and not albums[i].error]
        try:
            numbers = parse_selection(raw, len(albums))
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            continue
        picked = [albums[n - 1] for n in numbers if not albums[n - 1].error]
        if picked:
            return picked
        console.print("[red]Those albums couldn't be read.[/]")


def choose_kinds(args, console) -> set:
    if args.images_only:
        return {"image"}
    if args.videos_only:
        return {"video"}
    if args.all or args.new_only or not sys.stdin.isatty():
        return {"image", "video"}
    answer = Prompt.ask("[bold]Files[/]", choices=["both", "images", "videos"], default="both", console=console)
    return {"both": {"image", "video"}, "images": {"image"}, "videos": {"video"}}[answer]


def download_selected(session, albums, base_folder, kinds, workers, history, console):
    rows = []
    planned = {a.id: [m for m in a.media if m.kind in kinds] for a in albums}
    with ui.make_progress(console) as progress:
        overall = progress.add_task("[bold]Total", total=sum(len(v) for v in planned.values()))
        for album in albums:
            media = planned[album.id]
            if not media:
                continue
            task = progress.add_task(album.title[:36], total=len(media))

            def tick(task=task):
                progress.advance(task)
                progress.advance(overall)

            folder = base_folder / f"{clean_name(album.title)}_{album.id}"
            counts = download_album(session, media, folder, workers, on_file=tick)
            rows.append((album.title, counts))
            if counts["failed"] == 0:
                history.mark(album.id, album.title, album.url, len(media))
    return rows


def run(args, console) -> int:
    cfg = load_config()
    output = Path(args.output or cfg["output"])
    workers = args.workers or cfg["workers"]
    delay = args.delay if args.delay is not None else cfg["delay"]
    proxy = args.proxy or cfg["proxy"]

    raw_urls = list(args.urls)
    if args.file:
        with open(args.file) as fh:
            raw_urls += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not raw_urls:
        if not sys.stdin.isatty():
            console.print("[red]Give a link, or run it in a terminal.[/]")
            return 2
        raw_urls = [Prompt.ask("[bold]Paste a profile or album link[/]")]

    interactive = not (args.all or args.new_only or args.list_only)
    if interactive and not sys.stdin.isatty():
        console.print("[red]No terminal for the menu. Use --all, --new-only or --list-only.[/]")
        return 2

    session = make_session(proxy, args.cookies)
    history = History()
    all_rows = []
    try:
        for raw in raw_urls:
            try:
                url = normalize_url(raw)
            except ValueError as exc:
                console.print(f"[red]{exc}[/]")
                continue

            if is_album_url(url):
                albums = [album_from_url(url)]
                title, folder = "Album", output
            else:
                name = profile_username(url)
                with console.status("Scanning profile…") as status:
                    albums = scan_profile(
                        session, url, delay,
                        on_page=lambda p, n: status.update(f"Scanning page {p}  ·  {n} albums"),
                    )
                if not albums:
                    console.print(f"[yellow]No albums found at {url}. The layout may have changed.[/]")
                    continue
                title, folder = f"@{name}", output / name

            load_details(session, albums, delay, workers, console)
            done = history.done_ids()

            if args.list_only:
                ui.show_albums(console, albums, done, title=title)
                continue
            if args.all:
                chosen = [a for a in albums if not a.error]
            elif args.new_only:
                chosen = [a for a in albums if a.id not in done and not a.error]
                if not chosen:
                    console.print("[yellow]Nothing new to download.[/]")
                    continue
            elif len(albums) == 1:
                ui.show_albums(console, albums, done, title=title)
                chosen = [a for a in albums if not a.error]
            else:
                chosen = choose_albums(console, albums, done, title)
            if not chosen:
                console.print("[dim]Nothing selected.[/]")
                continue

            kinds = choose_kinds(args, console)
            all_rows += download_selected(session, chosen, folder, kinds, workers, history, console)
    finally:
        history.close()

    if all_rows:
        ui.summary(console, all_rows, output.resolve())
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()
    ui.banner(console, __version__)
    try:
        return run(args, console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped. Partial files resume on the next run.[/]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
