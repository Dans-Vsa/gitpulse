"""Command-line interface for gitpulse."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from gitpulse import __version__
from gitpulse.authors import SORT_KEYS, author_stats
from gitpulse.filters import filter_by_author
from gitpulse.git import GitError, find_repo_root, git_version, repo_info
from gitpulse.heatmap import (
    WEEKDAYS,
    Calendar,
    build_calendar,
    busiest_slot,
    daily_counts,
    level,
    weekday_hour_grid,
)
from gitpulse.history import LogOptions, read_commits
from gitpulse.hotspots import HOTSPOT_SORT_KEYS, dir_hotspots, file_hotspots
from gitpulse.models import Commit
from gitpulse.stats import summarize

app = typer.Typer(
    name="gitpulse",
    help="Terminal analytics for git repositories.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)
BAR_WIDTH = 6

RepoPath = Annotated[
    Path,
    typer.Argument(help="Path inside the git repository to analyse.", show_default="."),
]
SinceOption = Annotated[
    Optional[str],
    typer.Option(help='Only commits after this date, e.g. "2026-01-01" or "3 months ago".'),
]
UntilOption = Annotated[Optional[str], typer.Option(help="Only commits before this date.")]
RevOption = Annotated[
    Optional[str],
    typer.Option("--rev", help="Branch, tag or revision range to read (default: HEAD)."),
]
AuthorOption = Annotated[
    Optional[list[str]],
    typer.Option(
        "--author",
        "-a",
        help="Only commits whose author name/email contains this text (repeatable).",
    ),
]
PathOption = Annotated[
    Optional[list[str]],
    typer.Option(
        "--path",
        "-p",
        help="Only changes under this path or git pathspec, e.g. src/ or '*.py' (repeatable).",
    ),
]
NoMergesOption = Annotated[bool, typer.Option("--no-merges", help="Skip merge commits.")]
JsonOption = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"gitpulse {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """gitpulse — contributors, hotspots, churn and activity for any git repo."""


def _fmt_date(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M %z") if value else "—"


@app.command()
def doctor(path: RepoPath = Path(".")) -> None:
    """Check that git works and show basic facts about a repository."""
    try:
        version = git_version()
        info = repo_info(path)
    except GitError as exc:
        err_console.print(f"[bold red]error:[/] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("git", version)
    table.add_row("repository", str(info.root))
    table.add_row("branch", info.branch or "(detached HEAD)")
    table.add_row("commits", str(info.commit_count))
    table.add_row("first commit", _fmt_date(info.first_commit))
    table.add_row("last commit", _fmt_date(info.last_commit))
    table.add_row("remote", info.remote_url or "—")

    console.print(table)
    if info.commit_count == 0:
        console.print("[yellow]No commits yet — nothing to analyse.[/]")
    else:
        console.print("[green]Ready.[/]")


def _load_commits(
    path: Path, options: LogOptions, authors: list[str] | None = None
) -> tuple[Path, list[Commit]]:
    try:
        root = find_repo_root(path)
        commits = read_commits(root, options)
    except GitError as exc:
        err_console.print(f"[bold red]error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    return root, filter_by_author(commits, authors)


@app.command()
def summary(
    path: RepoPath = Path("."),
    since: SinceOption = None,
    until: UntilOption = None,
    rev: RevOption = None,
    author: AuthorOption = None,
    paths: PathOption = None,
    no_merges: NoMergesOption = False,
    as_json: JsonOption = False,
) -> None:
    """Overview of the history: commits, authors, lines changed, active days."""
    options = LogOptions(
        since=since, until=until, rev=rev, paths=tuple(paths or ()), include_merges=not no_merges
    )
    root, commits = _load_commits(path, options, author)
    s = summarize(commits)

    if as_json:
        typer.echo(json.dumps({"repository": str(root), **s.to_dict()}, indent=2))
        return

    if s.commits == 0:
        console.print(f"[yellow]No commits found in[/] {root}")
        return

    day = "%Y-%m-%d"
    table = Table(title=f"gitpulse · {root.name}", show_header=False, title_justify="left")
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(justify="right")
    table.add_row("Commits", f"{s.commits:,} ({s.merges:,} merges)")
    table.add_row("Authors", f"{s.authors:,}")
    table.add_row("First commit", s.first_commit.strftime(day))
    table.add_row("Last commit", s.last_commit.strftime(day))
    table.add_row("Active days", f"{s.active_days:,} of {s.span_days:,}")
    table.add_row("Commits / active day", f"{s.commits_per_active_day:.2f}")
    table.add_row("Lines", f"[green]+{s.lines_added:,}[/] [red]-{s.lines_deleted:,}[/] (net {s.net_lines:+,})")
    table.add_row("Files touched", f"{s.files_touched:,}")
    table.add_row("Busiest day", f"{s.busiest_day:{day}} ({s.busiest_day_commits} commits)")
    table.add_row("Top author", f"{s.top_author} ({s.top_author_commits} commits)")
    console.print(table)


@app.command()
def authors(
    path: RepoPath = Path("."),
    since: SinceOption = None,
    until: UntilOption = None,
    rev: RevOption = None,
    author: AuthorOption = None,
    paths: PathOption = None,
    top: Annotated[
        Optional[int], typer.Option("--top", "-n", min=1, help="Show only the first N authors.")
    ] = None,
    sort: Annotated[
        str,
        typer.Option(
            "--sort", "-s", help=f"Sort by: {', '.join(SORT_KEYS)}.", case_sensitive=False
        ),
    ] = "commits",
    emails: Annotated[bool, typer.Option("--emails", help="Show author emails.")] = False,
    no_merges: NoMergesOption = False,
    as_json: JsonOption = False,
) -> None:
    """Per-contributor stats: commits, share, lines, files, first/last commit."""
    sort = sort.lower()
    if sort not in SORT_KEYS:
        err_console.print(f"[bold red]error:[/] --sort must be one of: {', '.join(SORT_KEYS)}")
        raise typer.Exit(code=2)

    options = LogOptions(
        since=since, until=until, rev=rev, paths=tuple(paths or ()), include_merges=not no_merges
    )
    root, commits = _load_commits(path, options, author)
    all_authors = author_stats(commits, sort_by=sort)
    shown = all_authors[:top] if top else all_authors

    if as_json:
        payload = {
            "repository": str(root),
            "commits": len(commits),
            "total_authors": len(all_authors),
            "sort": sort,
            "authors": [a.to_dict() for a in shown],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if not commits:
        console.print(f"[yellow]No commits found in[/] {root}")
        return

    day = "%Y-%m-%d"
    table = Table(
        title=f"gitpulse · authors · {root.name}",
        title_justify="left",
        box=box.SIMPLE_HEAD,
        show_edge=False,
        padding=(0, 1, 0, 0),
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Author", style="bold", min_width=12)
    table.add_column("Commits", justify="right")
    table.add_column("%", justify="right")
    table.add_column("+", justify="right", style="green")
    table.add_column("-", justify="right", style="red")
    table.add_column("Files", justify="right")
    table.add_column("Days", justify="right")
    table.add_column("First", justify="right", no_wrap=True)
    table.add_column("Last", justify="right", no_wrap=True)
    for rank, a in enumerate(shown, start=1):
        label = a.name
        if emails:
            label += f" [dim]<{a.email}>[/]"
        if a.aliases:
            label += f"\n[dim]aka {', '.join(a.aliases)}[/]"
        table.add_row(
            str(rank),
            label,
            f"{a.commits:,}",
            f"{a.share:.0%}",
            f"{a.lines_added:,}",
            f"{a.lines_deleted:,}",
            f"{a.files_touched:,}",
            f"{a.active_days:,}",
            a.first_commit.strftime(day),
            a.last_commit.strftime(day),
        )
    console.print(table)
    if len(shown) < len(all_authors):
        console.print(f"[dim]Showing {len(shown)} of {len(all_authors)} authors (--top).[/]")


@app.command()
def hotspots(
    path: RepoPath = Path("."),
    since: SinceOption = None,
    until: UntilOption = None,
    rev: RevOption = None,
    author: AuthorOption = None,
    paths: PathOption = None,
    depth: Annotated[
        Optional[int],
        typer.Option(
            "--depth", "-d", min=1, help="Roll files up into directories N levels deep."
        ),
    ] = None,
    top: Annotated[int, typer.Option("--top", "-n", min=1, help="How many rows to show.")] = 20,
    sort: Annotated[
        str,
        typer.Option(
            "--sort",
            "-s",
            help=f"Sort by: {', '.join(HOTSPOT_SORT_KEYS)}.",
            case_sensitive=False,
        ),
    ] = "churn",
    no_merges: NoMergesOption = False,
    as_json: JsonOption = False,
) -> None:
    """Most-changed files (or directories with --depth): churn, commits, authors."""
    sort = sort.lower()
    if sort not in HOTSPOT_SORT_KEYS:
        err_console.print(
            f"[bold red]error:[/] --sort must be one of: {', '.join(HOTSPOT_SORT_KEYS)}"
        )
        raise typer.Exit(code=2)

    options = LogOptions(
        since=since, until=until, rev=rev, paths=tuple(paths or ()), include_merges=not no_merges
    )
    root, commits = _load_commits(path, options, author)
    if depth:
        spots = dir_hotspots(commits, depth=depth, sort_by=sort)
    else:
        spots = file_hotspots(commits, sort_by=sort)
    shown = spots[:top]
    kind = "directories" if depth else "files"

    if as_json:
        payload = {
            "repository": str(root),
            "commits": len(commits),
            "kind": kind,
            "depth": depth,
            "sort": sort,
            f"total_{kind}": len(spots),
            "hotspots": [s.to_dict() for s in shown],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if not spots:
        console.print(f"[yellow]No changes found in[/] {root}")
        return

    max_churn = max(s.churn for s in shown) or 1
    table = Table(
        title=f"gitpulse · hotspots ({kind}) · {root.name}",
        title_justify="left",
        box=box.SIMPLE_HEAD,
        show_edge=False,
        padding=(0, 1, 0, 0),
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Directory" if depth else "File", style="bold", min_width=20, overflow="fold")
    table.add_column("Churn", justify="right")
    table.add_column("", no_wrap=True, style="magenta", width=BAR_WIDTH)
    table.add_column("Commits", justify="right")
    table.add_column("Authors", justify="right")
    if depth:
        table.add_column("Files", justify="right")
    table.add_column("Last", justify="right", no_wrap=True)
    for rank, s in enumerate(shown, start=1):
        bar = "█" * max(1, round(BAR_WIDTH * s.churn / max_churn)) if s.churn else ""
        name = s.path + (" [dim](binary)[/]" if s.binary and not depth else "")
        row = [
            str(rank),
            name,
            f"{s.churn:,}",
            bar,
            f"{s.commits:,}",
            f"{s.authors:,}",
        ]
        if depth:
            row.append(f"{s.file_count:,}")
        row.append(s.last_changed.strftime("%Y-%m-%d"))
        table.add_row(*row)
    console.print(table)
    if len(shown) < len(spots):
        console.print(f"[dim]Showing {len(shown)} of {len(spots)} {kind} (--top).[/]")


HEAT_GLYPHS = ("·", "░", "▒", "▓", "█")
HEAT_STYLES = ("grey35", "green4", "green3", "green1", "bold bright_green")
HEAT_VIEWS = ("both", "hours", "calendar")


def _heat_cell(count: int, peak: int, width: int) -> Text:
    lvl = level(count, peak)
    return Text(HEAT_GLYPHS[lvl] * width, style=HEAT_STYLES[lvl])


def _legend() -> Text:
    text = Text("less ", style="dim")
    for glyph, style in zip(HEAT_GLYPHS, HEAT_STYLES):
        text.append(glyph * 2, style=style)
        text.append(" ")
    text.append("more", style="dim")
    return text


def _render_hours(grid: list[list[int]], utc: bool) -> None:
    peak = max(max(row) for row in grid)
    header = Text("    ")
    for hour in range(0, 24, 3):
        header.append(f"{hour:02d}".ljust(9), style="dim")
    console.print(Text(f"Commits by weekday and hour ({'UTC' if utc else 'author local time'})",
                       style="bold"))
    console.print(header)
    for wd, row in enumerate(grid):
        line = Text(f"{WEEKDAYS[wd]} ", style="cyan")
        for hour, count in enumerate(row):
            if hour:
                line.append(" ")
            line.append_text(_heat_cell(count, peak, 2))
        line.append(f" {sum(row):>3}", style="dim")
        console.print(line, no_wrap=True, overflow="ignore", crop=False)


def _render_calendar(cal: Calendar) -> None:
    peak = cal.peak
    console.print(
        Text(f"Daily commits {cal.start:%Y-%m-%d} → {cal.end:%Y-%m-%d} ({cal.total:,} commits)",
             style="bold")
    )
    months = Text("     ")
    pending = ""
    for label in cal.month_labels():
        # Each week column is two characters wide; long labels spill into the next column.
        pending = label or pending[2:]
        months.append(pending[:2].ljust(2), style="dim")
    console.print(months)
    for wd in range(7):
        line = Text(f"{WEEKDAYS[wd]}  " if wd % 2 == 0 else "     ", style="cyan")
        for col in cal.weeks:
            day = col[wd]
            if day is None:
                line.append("  ")
            else:
                line.append_text(_heat_cell(cal.counts[day], peak, 1))
                line.append(" ")
        console.print(line)


@app.command()
def heatmap(
    path: RepoPath = Path("."),
    since: SinceOption = None,
    until: UntilOption = None,
    rev: RevOption = None,
    author: AuthorOption = None,
    paths: PathOption = None,
    view: Annotated[
        str,
        typer.Option("--view", help=f"What to draw: {', '.join(HEAT_VIEWS)}.", case_sensitive=False),
    ] = "both",
    weeks: Annotated[
        int, typer.Option("--weeks", "-w", min=1, max=104, help="Calendar width in weeks.")
    ] = 26,
    utc: Annotated[bool, typer.Option("--utc", help="Use UTC instead of each author's clock.")] = False,
    no_merges: NoMergesOption = False,
    as_json: JsonOption = False,
) -> None:
    """When does work happen? Weekday × hour grid and a GitHub-style calendar."""
    view = view.lower()
    if view not in HEAT_VIEWS:
        err_console.print(f"[bold red]error:[/] --view must be one of: {', '.join(HEAT_VIEWS)}")
        raise typer.Exit(code=2)

    options = LogOptions(
        since=since, until=until, rev=rev, paths=tuple(paths or ()), include_merges=not no_merges
    )
    root, commits = _load_commits(path, options, author)
    grid = weekday_hour_grid(commits, utc=utc)
    counts = daily_counts(commits, utc=utc)
    end = max(counts) if counts else None
    cal = build_calendar(counts, end, weeks) if end else None
    slot = busiest_slot(grid)

    if as_json:
        payload = {
            "repository": str(root),
            "commits": len(commits),
            "timezone": "utc" if utc else "author",
            "weekdays": list(WEEKDAYS),
            "hours": grid,
            "busiest": (
                {"weekday": WEEKDAYS[slot[0]], "hour": slot[1], "commits": slot[2]}
                if slot else None
            ),
            "days": {d.isoformat(): n for d, n in sorted(counts.items())},
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if not commits:
        console.print(f"[yellow]No commits found in[/] {root}")
        return

    console.print(Text(f"gitpulse · heatmap · {root.name}", style="italic"))
    if view in ("both", "hours"):
        _render_hours(grid, utc)
        console.print()
    if view in ("both", "calendar") and cal:
        _render_calendar(cal)
        console.print()
    console.print(_legend())
    if slot:
        wd, hour, n = slot
        console.print(
            f"Busiest slot: [bold]{WEEKDAYS[wd]} {hour:02d}:00–{hour:02d}:59[/] ({n} commits)"
        )
