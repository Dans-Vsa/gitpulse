import json
from datetime import date
from pathlib import Path

import pytest

from gitpulse.authors import author_stats, sort_authors
from gitpulse.history import read_commits


@pytest.fixture
def stats(history_repo: Path):
    return author_stats(read_commits(history_repo))


def test_author_stats_empty():
    assert author_stats([]) == []


def test_author_stats_merges_case_variant_emails(stats):
    assert [a.name for a in stats] == ["Alice", "Bob"]
    alice, bob = stats

    assert (alice.commits, alice.merges) == (4, 1)
    assert (alice.lines_added, alice.lines_deleted) == (6, 1)
    assert alice.files_touched == 2
    assert alice.active_days == 4
    assert alice.aliases == []

    assert (bob.commits, bob.merges) == (3, 0)
    assert (bob.lines_added, bob.lines_deleted) == (3, 2)
    assert bob.files_touched == 2  # src/app.py + binary logo.png
    assert bob.active_days == 2
    # The newest spelling is shown; the other one is kept as an alias.
    assert bob.email == "BOB@example.com"
    assert bob.aliases == ["bob@example.com"]


def test_author_stats_first_last_and_share(stats):
    alice, bob = stats
    assert alice.first_commit.date() == date(2026, 3, 1)
    assert alice.last_commit.date() == date(2026, 3, 5)
    assert bob.last_commit.date() == date(2026, 3, 4)
    assert alice.share == pytest.approx(4 / 7)
    assert sum(a.share for a in stats) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("commits", ["Alice", "Bob"]),
        ("lines", ["Alice", "Bob"]),
        ("added", ["Alice", "Bob"]),
        ("deleted", ["Bob", "Alice"]),
        ("files", ["Alice", "Bob"]),  # tie on files -> more commits first
        ("first", ["Alice", "Bob"]),
        ("last", ["Alice", "Bob"]),
        ("name", ["Alice", "Bob"]),
    ],
)
def test_sort_authors(stats, key, expected):
    assert [a.name for a in sort_authors(stats, key)] == expected


def test_sort_authors_rejects_unknown_key(stats):
    with pytest.raises(ValueError, match="unknown sort key"):
        sort_authors(stats, "karma")


def test_author_to_dict_is_json_friendly(stats):
    d = stats[1].to_dict()
    assert json.loads(json.dumps(d)) == d
    assert d["aliases"] == ["bob@example.com"]
    assert d["share"] == round(3 / 7, 4)
    assert d["first_commit"].startswith("2026-03-01T15:30:00")
