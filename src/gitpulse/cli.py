"""Command-line interface for gitpulse."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from gitpulse import __version__
from gitpulse.git import GitError, git_version, repo_info

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
