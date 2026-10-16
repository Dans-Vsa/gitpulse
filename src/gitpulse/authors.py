"""Per-author statistics for ``gitpulse authors``.

Identities are merged by email, case-insensitively (see ``stats.author_key``),
after git has applied the repository's ``.mailmap``. Every distinct name and
email seen for a merged identity is kept as an alias so the merge is visible.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime

from gitpulse.models import Commit
from gitpulse.stats import author_key

SORT_KEYS = ("commits", "lines", "added", "deleted", "files", "first", "last", "name")


@dataclass(slots=True)
class AuthorStats:
    """Aggregated activity of one (merged) contributor."""

    key: str
    name: str
    email: str
    commits: int = 0
    merges: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    names: set[str] = field(default_factory=set)
    emails: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)
    days: set[date] = field(default_factory=set)
    share: float = 0.0

    @property
    def lines_changed(self) -> int:
        return self.lines_added + self.lines_deleted

    @property
    def files_touched(self) -> int:
        return len(self.files)

    @property
    def active_days(self) -> int:
        return len(self.days)

    @property
    def aliases(self) -> list[str]:
        """Other names/emails merged into this identity, sorted."""
        others = (self.names - {self.name}) | (self.emails - {self.email})
        return sorted(others, key=str.lower)

    def add(self, commit: Commit) -> None:
        self.commits += 1
        self.merges += commit.is_merge
        self.lines_added += commit.added
        self.lines_deleted += commit.deleted
        self.names.add(commit.author_name)
        self.emails.add(commit.author_email)
        self.files.update(f.path for f in commit.files)
        self.days.add(commit.authored_at.date())
        when = commit.authored_at
        if self.first_commit is None or when < self.first_commit:
            self.first_commit = when
        if self.last_commit is None or when > self.last_commit:
            self.last_commit = when

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "aliases": self.aliases,
            "commits": self.commits,
            "share": round(self.share, 4),
            "merges": self.merges,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "files_touched": self.files_touched,
            "active_days": self.active_days,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
        }


def _sort_value(author: AuthorStats, key: str):
    return {
        "commits": author.commits,
        "lines": author.lines_changed,
        "added": author.lines_added,
        "deleted": author.lines_deleted,
        "files": author.files_touched,
        "first": author.first_commit,
        "last": author.last_commit,
    }[key]


def sort_authors(authors: list[AuthorStats], by: str = "commits") -> list[AuthorStats]:
    """Sort descending by ``by`` (``first`` is ascending, ``name`` alphabetical).

    Ties are broken by commit count, then name, so the output is stable.
    """
    if by not in SORT_KEYS:
        raise ValueError(f"unknown sort key {by!r}; choose from {', '.join(SORT_KEYS)}")
    alphabetical = sorted(authors, key=lambda a: a.name.lower())
    if by == "name":
        return alphabetical
    if by == "first":
        return sorted(alphabetical, key=lambda a: a.first_commit)
    return sorted(
        alphabetical, key=lambda a: (_sort_value(a, by), a.commits), reverse=True
    )


def author_stats(commits: Iterable[Commit], sort_by: str = "commits") -> list[AuthorStats]:
    """Group ``commits`` (newest first) by author and return sorted ``AuthorStats``."""
    by_key: dict[str, AuthorStats] = {}
    total = 0
    for commit in commits:
        total += 1
        key = author_key(commit)
        if key not in by_key:
            # Newest first, so the most recent spelling becomes the display name.
            by_key[key] = AuthorStats(key=key, name=commit.author_name, email=commit.author_email)
        by_key[key].add(commit)

    for author in by_key.values():
        author.share = author.commits / total
    return sort_authors(list(by_key.values()), sort_by)
