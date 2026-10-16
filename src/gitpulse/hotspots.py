"""Hotspots: the files and directories that change the most.

Churn is ``lines added + lines deleted``. A file that is edited often and in
large chunks is a classic sign of code that is hard to get right, so these
lists are a good starting point for reviews and refactoring.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath

from gitpulse.models import Commit
from gitpulse.stats import author_key

HOTSPOT_SORT_KEYS = ("churn", "commits", "added", "deleted", "authors", "last", "path")
ROOT = "."


@dataclass(slots=True)
class Hotspot:
    """Change statistics for one file or one directory."""

    path: str
    commits: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    binary: bool = False
    last_changed: datetime | None = None
    author_keys: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)

    @property
    def churn(self) -> int:
        return self.lines_added + self.lines_deleted

    @property
    def authors(self) -> int:
        return len(self.author_keys)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "commits": self.commits,
            "churn": self.churn,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "authors": self.authors,
            "files": self.file_count,
            "binary": self.binary,
            "last_changed": self.last_changed.isoformat() if self.last_changed else None,
        }


def directory_of(path: str, depth: int) -> str:
    """The first ``depth`` directory components of ``path`` (``.`` for top-level files).

    >>> directory_of("src/gitpulse/cli.py", 1)
    'src'
    >>> directory_of("src/gitpulse/cli.py", 2)
    'src/gitpulse'
    >>> directory_of("README.md", 1)
    '.'
    """
    if depth < 1:
        raise ValueError("depth must be at least 1")
    parents = PurePosixPath(path).parts[:-1]
    if not parents:
        return ROOT
    return "/".join(parents[:depth])


def _collect(commits: Iterable[Commit], key_for) -> dict[str, Hotspot]:
    spots: dict[str, Hotspot] = {}
    for commit in commits:
        who = author_key(commit)
        touched: set[str] = set()
        for change in commit.files:
            key = key_for(change.path)
            spot = spots.get(key)
            if spot is None:
                spot = spots[key] = Hotspot(path=key)
            spot.lines_added += change.added
            spot.lines_deleted += change.deleted
            spot.binary = spot.binary or change.binary
            spot.author_keys.add(who)
            spot.files.add(change.path)
            if spot.last_changed is None or commit.authored_at > spot.last_changed:
                spot.last_changed = commit.authored_at
            touched.add(key)
        # A commit counts once per directory, even if it edits several files there.
        for key in touched:
            spots[key].commits += 1
    return spots


def sort_hotspots(spots: list[Hotspot], by: str = "churn") -> list[Hotspot]:
    """Sort descending by ``by`` (``path`` is alphabetical); ties broken by path."""
    if by not in HOTSPOT_SORT_KEYS:
        raise ValueError(f"unknown sort key {by!r}; choose from {', '.join(HOTSPOT_SORT_KEYS)}")
    alphabetical = sorted(spots, key=lambda s: s.path.lower())
    if by == "path":
        return alphabetical
    value = {
        "churn": lambda s: (s.churn, s.commits),
        "commits": lambda s: (s.commits, s.churn),
        "added": lambda s: (s.lines_added, s.commits),
        "deleted": lambda s: (s.lines_deleted, s.commits),
        "authors": lambda s: (s.authors, s.commits),
        "last": lambda s: s.last_changed,
    }[by]
    return sorted(alphabetical, key=value, reverse=True)


def file_hotspots(commits: Iterable[Commit], sort_by: str = "churn") -> list[Hotspot]:
    """Per-file hotspots. Paths are as git reports them (renames are not followed)."""
    return sort_hotspots(list(_collect(commits, lambda p: p).values()), sort_by)


def dir_hotspots(
    commits: Iterable[Commit], depth: int = 1, sort_by: str = "churn"
) -> list[Hotspot]:
    """Hotspots rolled up to directories ``depth`` levels deep."""
    spots = _collect(commits, lambda p: directory_of(p, depth))
    return sort_hotspots(list(spots.values()), sort_by)
