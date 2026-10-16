from datetime import datetime, timezone
from pathlib import Path

from gitpulse.filters import filter_by_author, matches_author
from gitpulse.history import LogOptions, read_commits
from gitpulse.models import Commit


def make(name: str, email: str) -> Commit:
    return Commit(
        sha="0" * 40,
        author_name=name,
        author_email=email,
        authored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        subject="x",
    )


def test_matches_author_name_or_email_case_insensitive():
    c = make("Alice Liddell", "alice@example.com")
    assert matches_author(c, ["alice"])
    assert matches_author(c, ["LIDDELL"])
    assert matches_author(c, ["@example.com"])
    assert matches_author(c, ["nobody", "liddell"])
    assert not matches_author(c, ["bob"])


def test_filter_by_author_without_patterns_keeps_everything():
    commits = [make("A", "a@x"), make("B", "b@x")]
    assert filter_by_author(commits, None) == commits
    assert filter_by_author(commits, []) == commits
    assert filter_by_author(commits, ["  "]) == commits


def test_filter_by_author_on_real_history(history_repo: Path):
    commits = read_commits(history_repo)
    bob = filter_by_author(commits, ["bob"])
    # Matches both bob@ and BOB@ spellings.
    assert len(bob) == 3
    assert {c.author_name for c in bob} == {"Bob"}
    both = filter_by_author(commits, ["alice", "bob"])
    assert len(both) == len(commits)


def test_path_filter_limits_commits_and_numstat(history_repo: Path):
    commits = read_commits(history_repo, LogOptions(paths=("src/",)))
    assert [c.subject for c in commits] == ["fix: app output", "feat: add app"]
    assert {f.path for c in commits for f in c.files} == {"src/app.py"}
