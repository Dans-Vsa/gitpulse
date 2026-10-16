"""Aggregate statistics computed from a list of commits."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from gitpulse.models import Commit


@dataclass(frozen=True, slots=True)
class Summary:
    """Headline numbers for ``gitpulse summary``."""

    commits: int
    merges: int
    authors: int
    first_commit: datetime | None
    last_commit: datetime | None
    active_days: int
    lines_added: int
    lines_deleted: int
    files_touched: int
    busiest_day: date | None
    busiest_day_commits: int
    top_author: str | None
    top_author_commits: int

    @property
    def span_days(self) -> int:
        """Calendar days from the first to the last commit, inclusive."""
        if self.first_commit is None or self.last_commit is None:
            return 0
        return (self.last_commit.date() - self.first_commit.date()).days + 1

    @property
    def net_lines(self) -> int:
        return self.lines_added - self.lines_deleted

    @property
    def commits_per_active_day(self) -> float:
        return self.commits / self.active_days if self.active_days else 0.0

    def to_dict(self) -> dict:
        """JSON-friendly representation (dates as ISO 8601 strings)."""
        return {
            "commits": self.commits,
            "merges": self.merges,
            "authors": self.authors,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
            "span_days": self.span_days,
            "active_days": self.active_days,
            "commits_per_active_day": round(self.commits_per_active_day, 2),
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "net_lines": self.net_lines,
            "files_touched": self.files_touched,
            "busiest_day": self.busiest_day.isoformat() if self.busiest_day else None,
            "busiest_day_commits": self.busiest_day_commits,
            "top_author": self.top_author,
            "top_author_commits": self.top_author_commits,
        }


EMPTY_SUMMARY = Summary(0, 0, 0, None, None, 0, 0, 0, 0, None, 0, None, 0)


def author_key(commit: Commit) -> str:
    """Identify an author by email (case-insensitive), falling back to the name."""
    return (commit.author_email or commit.author_name).strip().lower()


def summarize(commits: list[Commit]) -> Summary:
    """Compute a ``Summary``; ``commits`` are expected newest first, as git returns them."""
    if not commits:
        return EMPTY_SUMMARY

    per_day = Counter(c.authored_at.date() for c in commits)
    per_author = Counter(author_key(c) for c in commits)
    display_names: dict[str, str] = {}
    for c in commits:
        # Newest first, so the most recent spelling of a name wins.
        display_names.setdefault(author_key(c), c.author_name)

    busiest_day, busiest_count = max(per_day.items(), key=lambda kv: (kv[1], kv[0]))
    top_key, top_count = per_author.most_common(1)[0]
    dates = [c.authored_at for c in commits]

    return Summary(
        commits=len(commits),
        merges=sum(c.is_merge for c in commits),
        authors=len(per_author),
        first_commit=min(dates),
        last_commit=max(dates),
        active_days=len(per_day),
        lines_added=sum(c.added for c in commits),
        lines_deleted=sum(c.deleted for c in commits),
        files_touched=len({f.path for c in commits for f in c.files}),
        busiest_day=busiest_day,
        busiest_day_commits=busiest_count,
        top_author=display_names[top_key],
        top_author_commits=top_count,
    )
