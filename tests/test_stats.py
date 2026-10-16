from datetime import date
from pathlib import Path

from gitpulse.history import read_commits
from gitpulse.stats import summarize


def test_summarize_empty():
    s = summarize([])
    assert s.commits == 0
    assert s.span_days == 0
    assert s.commits_per_active_day == 0.0
    assert s.top_author is None
    assert s.to_dict()["first_commit"] is None


def test_summarize_history_repo(history_repo: Path):
    s = summarize(read_commits(history_repo))
    assert s.commits == 7
    assert s.merges == 1
    # Bob's two emails differ only in case, so they count as one author.
    assert s.authors == 2
    assert s.first_commit.date() == date(2026, 3, 1)
    assert s.last_commit.date() == date(2026, 3, 5)
    assert s.span_days == 5
    assert s.active_days == 4
    assert (s.busiest_day, s.busiest_day_commits) == (date(2026, 3, 1), 3)
    assert s.files_touched == 4
    assert (s.lines_added, s.lines_deleted, s.net_lines) == (9, 3, 6)
    assert s.commits_per_active_day == 7 / 4
    assert (s.top_author, s.top_author_commits) == ("Alice", 4)


def test_summary_to_dict_is_json_friendly(history_repo: Path):
    d = summarize(read_commits(history_repo)).to_dict()
    assert d["busiest_day"] == "2026-03-01"
    assert d["first_commit"].startswith("2026-03-01T09:00:00")
    assert d["commits_per_active_day"] == 1.75
