"""Activity heatmaps: a weekday × hour grid and a GitHub-style calendar.

Times are taken in each commit's own timezone by default, which answers
"when do people work?" (a commit at 21:00 in Jakarta stays 21:00). Pass
``utc=True`` to put every commit on the same clock instead.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from gitpulse.models import Commit

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
LEVELS = 4  # intensity levels above zero, like GitHub's contribution graph


def _when(commit: Commit, utc: bool) -> datetime:
    return commit.authored_at.astimezone(timezone.utc) if utc else commit.authored_at


def weekday_hour_grid(commits: Iterable[Commit], utc: bool = False) -> list[list[int]]:
    """7 × 24 commit counts: ``grid[weekday][hour]`` with Monday = 0."""
    grid = [[0] * 24 for _ in range(7)]
    for commit in commits:
        when = _when(commit, utc)
        grid[when.weekday()][when.hour] += 1
    return grid


def daily_counts(commits: Iterable[Commit], utc: bool = False) -> Counter[date]:
    """Commits per calendar day."""
    return Counter(_when(c, utc).date() for c in commits)


def level(count: int, peak: int) -> int:
    """Map a count to 0..LEVELS; any non-zero count is at least level 1."""
    if count <= 0 or peak <= 0:
        return 0
    return max(1, min(LEVELS, -(-count * LEVELS // peak)))  # ceil(count / peak * LEVELS)


@dataclass(frozen=True, slots=True)
class Calendar:
    """Day counts laid out in week columns (Monday first), ending at ``end``."""

    start: date
    end: date
    weeks: list[list[date | None]]  # weeks[col][weekday]; None = outside the range
    counts: Counter[date]

    @property
    def peak(self) -> int:
        return max((self.counts[d] for col in self.weeks for d in col if d), default=0)

    @property
    def total(self) -> int:
        return sum(self.counts[d] for col in self.weeks for d in col if d)

    def month_labels(self) -> list[str]:
        """Per week column: a 3-letter month name where a new month starts, else ``""``."""
        labels: list[str] = []
        previous = None
        for col in self.weeks:
            first = next(d for d in col if d)
            month = first.month
            labels.append(first.strftime("%b") if month != previous else "")
            previous = month
        return labels


def build_calendar(counts: Counter[date], end: date, weeks: int = 26) -> Calendar:
    """Lay out the ``weeks`` most recent weeks up to and including ``end``."""
    if weeks < 1:
        raise ValueError("weeks must be at least 1")
    last_monday = end - timedelta(days=end.weekday())
    first_monday = last_monday - timedelta(weeks=weeks - 1)
    columns: list[list[date | None]] = []
    for w in range(weeks):
        monday = first_monday + timedelta(weeks=w)
        columns.append(
            [day if (day := monday + timedelta(days=i)) <= end else None for i in range(7)]
        )
    return Calendar(start=first_monday, end=end, weeks=columns, counts=counts)


def busiest_slot(grid: list[list[int]]) -> tuple[int, int, int] | None:
    """``(weekday, hour, commits)`` of the busiest cell, or ``None`` if the grid is empty."""
    best = max(
        ((wd, hr, n) for wd, row in enumerate(grid) for hr, n in enumerate(row)),
        key=lambda t: (t[2], -t[0], -t[1]),
    )
    return best if best[2] else None
