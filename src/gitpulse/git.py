"""Thin, testable wrapper around the ``git`` executable."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class GitError(RuntimeError):
    """Raised when git is missing or a git command fails."""


def parse_git_date(text: str) -> datetime:
    """Parse a strict ISO 8601 date from git (``%aI``), including the ``Z`` suffix.

    ``datetime.fromisoformat`` only understands ``Z`` from Python 3.11 on, and git
    prints ``Z`` for commits made in UTC.
    """
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def git_executable() -> str:
    """Return the path of the git binary or raise ``GitError``."""
    exe = shutil.which("git")
    if exe is None:
        raise GitError("git executable not found on PATH")
    return exe


def run_git(args: list[str], cwd: Path | str) -> str:
    """Run ``git <args>`` inside ``cwd`` and return stdout as text.

    Output is decoded as UTF-8 regardless of the console code page so author
    names and file paths survive on Windows.
    """
    proc = subprocess.run(
        [git_executable(), *args],
        cwd=str(cwd),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(message or f"git {' '.join(args)} failed ({proc.returncode})")
    return proc.stdout.decode("utf-8", errors="replace")


def git_version() -> str:
    """Return the installed git version, e.g. ``2.51.1``."""
    out = run_git(["--version"], cwd=Path.cwd()).strip()
    return out.removeprefix("git version ").split(" ")[0]


def find_repo_root(path: Path | str) -> Path:
    """Return the top-level directory of the repository containing ``path``."""
    start = Path(path)
    if not start.exists():
        raise GitError(f"path does not exist: {start}")
    if start.is_file():
        start = start.parent
    try:
        out = run_git(["rev-parse", "--show-toplevel"], cwd=start)
    except GitError as exc:
        raise GitError(f"not a git repository: {start}") from exc
    return Path(out.strip()).resolve()


@dataclass(frozen=True)
class RepoInfo:
    """Basic facts about a repository, shown by ``gitpulse doctor``."""

    root: Path
    branch: str | None
    commit_count: int
    first_commit: datetime | None
    last_commit: datetime | None
    remote_url: str | None


def _optional(args: list[str], cwd: Path) -> str | None:
    try:
        value = run_git(args, cwd=cwd).strip()
    except GitError:
        return None
    return value or None


def repo_info(path: Path | str) -> RepoInfo:
    """Collect ``RepoInfo`` for the repository containing ``path``.

    Works for freshly initialised repositories that have no commits yet.
    """
    root = find_repo_root(path)
    branch = _optional(["symbolic-ref", "--short", "-q", "HEAD"], root)
    has_commits = _optional(["rev-parse", "-q", "--verify", "HEAD"], root) is not None

    count = 0
    first = last = None
    if has_commits:
        count = int(run_git(["rev-list", "--count", "HEAD"], cwd=root).strip())
        dates = run_git(["log", "--format=%aI", "HEAD"], cwd=root).split()
        last = parse_git_date(dates[0])
        first = parse_git_date(dates[-1])

    return RepoInfo(
        root=root,
        branch=branch,
        commit_count=count,
        first_commit=first,
        last_commit=last,
        remote_url=_optional(["config", "--get", "remote.origin.url"], root),
    )
