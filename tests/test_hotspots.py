import json
from datetime import date
from pathlib import Path

import pytest

from gitpulse.history import read_commits
from gitpulse.hotspots import dir_hotspots, directory_of, file_hotspots, sort_hotspots


@pytest.fixture
def commits(history_repo: Path):
    return read_commits(history_repo)


@pytest.mark.parametrize(
    ("path", "depth", "expected"),
    [
        ("README.md", 1, "."),
        ("src/app.py", 1, "src"),
        ("src/gitpulse/cli.py", 1, "src"),
        ("src/gitpulse/cli.py", 2, "src/gitpulse"),
        ("src/gitpulse/cli.py", 5, "src/gitpulse"),
    ],
)
def test_directory_of(path, depth, expected):
    assert directory_of(path, depth) == expected


def test_directory_of_rejects_zero_depth():
    with pytest.raises(ValueError):
        directory_of("a/b.py", 0)


def test_file_hotspots(commits):
    spots = file_hotspots(commits)
    assert [s.path for s in spots] == ["README.md", "src/app.py", "notes.txt", "logo.png"]
    readme, app, notes, logo = spots
    assert (readme.commits, readme.lines_added, readme.lines_deleted, readme.churn) == (2, 5, 1, 6)
    assert (app.commits, app.churn, app.authors) == (2, 5, 1)  # bob@ and BOB@ are one author
    assert app.last_changed.date() == date(2026, 3, 4)
    assert logo.binary and logo.churn == 0 and logo.commits == 1
    assert not readme.binary


def test_dir_hotspots_counts_each_commit_once_per_directory(commits):
    spots = dir_hotspots(commits, depth=1)
    assert [s.path for s in spots] == [".", "src"]
    top, src = spots
    assert (top.churn, top.commits, top.file_count, top.authors) == (7, 4, 3, 2)
    assert (src.churn, src.commits, src.file_count) == (5, 2, 1)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("churn", ["README.md", "src/app.py", "notes.txt", "logo.png"]),
        ("commits", ["README.md", "src/app.py", "notes.txt", "logo.png"]),
        ("deleted", ["src/app.py", "README.md", "logo.png", "notes.txt"]),
        ("authors", ["README.md", "src/app.py", "logo.png", "notes.txt"]),
        ("last", ["notes.txt", "src/app.py", "README.md", "logo.png"]),
        ("path", ["logo.png", "notes.txt", "README.md", "src/app.py"]),
    ],
)
def test_sort_hotspots(commits, key, expected):
    assert [s.path for s in file_hotspots(commits, sort_by=key)] == expected


def test_sort_hotspots_rejects_unknown_key(commits):
    with pytest.raises(ValueError, match="unknown sort key"):
        sort_hotspots(file_hotspots(commits), "size")


def test_hotspot_to_dict(commits):
    d = file_hotspots(commits)[0].to_dict()
    assert json.loads(json.dumps(d)) == d
    assert d["path"] == "README.md" and d["churn"] == 6 and d["files"] == 1


def test_hotspots_empty():
    assert file_hotspots([]) == []
    assert dir_hotspots([], depth=2) == []
