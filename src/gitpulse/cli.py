"""Command-line interface for gitpulse."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from gitpulse import __version__
from gitpulse.git import GitError, find_repo_root, git_version, repo_info
from gitpulse.history import LogOptions, read_commits
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


def _load_commits(path: Path, options: LogOptions) -> tuple[Path, list[Commit]]:
    try:
        root = find_repo_root(path)
        return root, read_commits(root, options)
    except GitError as exc:
        err_console.print(f"[bold red]error:[/] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def summary(
    path: RepoPath = Path("."),
    since: SinceOption = None,
    until: UntilOption = None,
    rev: RevOption = None,
    no_merges: Annotated[bool, typer.Option("--no-merges", help="Skip merge commits.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    """Overview of the history: commits, authors, lines changed, active days."""
    options = LogOptions(since=since, until=until, rev=rev, include_merges=not no_merges)
    root, commits = _load_commits(path, options)
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
