"""All the terminal visuals live here."""
from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

ACCENT = "#ff4d8d"


def banner(console: Console, version: str) -> None:
    title = Text.assemble(("erome", "bold white"), ("-dl", f"bold {ACCENT}"))
    sub = Text("profile  →  pick  →  download", style="dim")
    body = Align.center(Text.assemble(title, "\n", sub))
    console.print(
        Panel(body, box=box.ROUNDED, border_style=ACCENT, padding=(1, 6), subtitle=f"v{version}"),
        justify="center",
    )


def show_albums(console: Console, albums, done_ids: set, view=None, title: str = "") -> None:
    view = list(range(len(albums))) if view is None else list(view)
    saved = sum(albums[i].id in done_ids for i in view)
    new = sum(albums[i].id not in done_ids and not albums[i].error for i in view)
    table = Table(
        title=title or None,
        title_style=f"bold {ACCENT}",
        box=box.ROUNDED,
        border_style="grey35",
        header_style="bold",
        caption=f"{len(view)} shown of {len(albums)}  ·  {new} new  ·  {saved} saved",
        caption_style="dim",
    )
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Album", max_width=54, overflow="ellipsis", no_wrap=True)
    table.add_column("Photos", justify="right")
    table.add_column("Videos", justify="right")
    table.add_column("Status", no_wrap=True)
    for i in view:
        a = albums[i]
        photos = str(a.photos) if a.loaded else "–"
        videos = str(a.videos) if a.loaded else "–"
        if a.error:
            status = "[red]✗ unreadable[/]"
        elif a.id in done_ids:
            status = "[green]✓ saved[/]"
        else:
            status = f"[{ACCENT}]● new[/]"
        table.add_row(str(i + 1), a.title, photos, videos, status)
    console.print(table)


def make_progress(console: Console, transient: bool = False) -> Progress:
    return Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn("[bold]{task.description}", justify="left"),
        BarColumn(complete_style=ACCENT, finished_style="green"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=transient,
    )


def summary(console: Console, rows, out_dir) -> None:
    table = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False)
    table.add_column("Album", max_width=48, overflow="ellipsis", no_wrap=True)
    table.add_column("New", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="dim")
    table.add_column("Failed", justify="right")
    for title, c in rows:
        failed = f"[red]{c['failed']}[/]" if c["failed"] else "0"
        table.add_row(title, str(c["ok"]), str(c["skipped"]), failed)
    total_ok = sum(c["ok"] for _, c in rows)
    total_failed = sum(c["failed"] for _, c in rows)
    footer = Text.assemble(
        (f"{total_ok} files saved", "bold green"),
        (f"  ·  {total_failed} failed" if total_failed else "", "red"),
        f"\n→ {out_dir}",
    )
    console.print(Panel(table, title="Done", border_style="green", box=box.ROUNDED))
    console.print(footer)
