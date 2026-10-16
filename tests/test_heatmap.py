from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from gitpulse.heatmap import (
    LEVELS,
    build_calendar,
    busiest_slot,
    daily_counts,
    level,
    weekday_hour_grid,
)
from gitpulse.history import read_commits

SUN, MON, TUE, WED, THU = 6, 0, 1, 2, 3


@pytest.fixture
def commits(history_repo: Path):
    return read_commits(history_repo)


def test_weekday_hour_grid(commits):
    grid = weekday_hour_grid(commits)
    assert len(grid) == 7 and all(len(row) == 24 for row in grid)
    assert sum(map(sum, grid)) == 7
    # 2026-03-01 is a Sunday: commits at 09:00, 15:30 and 16:00 UTC.
    assert (grid[SUN][9], grid[SUN][15], grid[SUN][16]) == (1, 1, 1)
    assert grid[TUE][11] == 1
    assert (grid[WED][20], grid[WED][21]) == (1, 1)
    assert grid[THU][8] == 1  # the merge commit


def test_grid_uses_author_clock_unless_utc(sample_repo: Path):
    commits = read_commits(sample_repo)
    # First commit: Monday 2026-01-05 09:00 +07:00 == 02:00 UTC.
    assert weekday_hour_grid(commits)[MON][9] == 1
    assert weekday_hour_grid(commits, utc=True)[MON][2] == 1


def test_daily_counts(commits):
    assert daily_counts(commits) == Counter(
        {date(2026, 3, 1): 3, date(2026, 3, 3): 1, date(2026, 3, 4): 2, date(2026, 3, 5): 1}
    )


@pytest.mark.parametrize(
    ("count", "peak", "expected"),
    [(0, 3, 0), (1, 3, 2), (2, 3, 3), (3, 3, 4), (1, 100, 1), (5, 0, 0), (100, 100, LEVELS)],
)
def test_level(count, peak, expected):
    assert level(count, peak) == expected


def test_build_calendar(commits):
    cal = build_calendar(daily_counts(commits), end=date(2026, 3, 5), weeks=2)
    assert cal.start == date(2026, 2, 23)  # a Monday
    assert len(cal.weeks) == 2 and all(len(col) == 7 for col in cal.weeks)
    assert cal.weeks[0][0] == date(2026, 2, 23)
    assert cal.weeks[0][6] == date(2026, 3, 1)
    assert cal.weeks[1][3] == date(2026, 3, 5)
    assert cal.weeks[1][4:] == [None, None, None]  # after the end date
    assert (cal.total, cal.peak) == (7, 3)
    assert cal.month_labels() == ["Feb", "Mar"]


def test_build_calendar_drops_days_before_window(commits):
    cal = build_calendar(daily_counts(commits), end=date(2026, 3, 5), weeks=1)
    assert cal.total == 4  # the three Sunday commits fall in the previous week


def test_build_calendar_rejects_zero_weeks():
    with pytest.raises(ValueError):
        build_calendar(Counter(), end=date(2026, 1, 1), weeks=0)


def test_busiest_slot(commits):
    # Every slot has one commit; ties go to the earliest weekday, then hour.
    assert busiest_slot(weekday_hour_grid(commits)) == (TUE, 11, 1)
    assert busiest_slot(weekday_hour_grid([])) is None
