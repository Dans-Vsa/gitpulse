from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitpulse.git import GitError
from gitpulse.history import (
    FIELD_SEP,
    RECORD_SEP,
    LogOptions,
    parse_log,
    parse_numstat,
    read_commits,
)

from conftest import commit


def _record(sha, parents, name, email, date, subject, numstat=""):
    header = FIELD_SEP.join([sha, parents, name, email, date, subject])
    return f"{RECORD_SEP}{header}\n{numstat}"


def test_parse_numstat_text_binary_and_garbage():
    assert parse_numstat("3\t1\tsrc/a b.py").added == 3
    binary = parse_numstat("-\t-\timg.png")
    assert binary.binary and binary.churn == 0
    assert parse_numstat("not numstat") is None
    assert parse_numstat("x\ty\tfile") is None


def test_parse_log_reads_header_and_numstat():
    raw = _record(
        "a" * 40, "b" * 40, "Ann", "ann@x.io", "2026-05-01T12:00:00+02:00", "feat: x",
        "\n3\t1\tsrc/a.py\n-\t-\timg.png\n",
    )
    [c] = parse_log(raw)
    assert c.author_name == "Ann"
    assert c.authored_at == datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    assert c.parents == ("b" * 40,)
    assert c.short_sha == "aaaaaaa"
    assert [f.path for f in c.files] == ["src/a.py", "img.png"]
    assert c.files[1].binary is True
    assert (c.added, c.deleted) == (3, 1)


def test_parse_log_handles_merges_and_odd_subjects():
    raw = _record("c" * 40, "a b", "Zoë", "z@x.io", "2026-05-01T12:00:00Z", "Merge: tabs\there")
    [c] = parse_log(raw)
    assert c.is_merge
    assert c.subject == "Merge: tabs\there"
    assert c.files == ()


def test_parse_log_root_commit_has_no_parents():
    [c] = parse_log(_record("d" * 40, "", "Ann", "a@x.io", "2026-05-01T12:00:00Z", "init"))
    assert c.parents == () and not c.is_merge


def test_parse_log_ignores_empty_input():
    assert parse_log("") == []


def test_parse_log_rejects_malformed_header():
    with pytest.raises(GitError, match="unexpected git log record"):
        parse_log(f"{RECORD_SEP}only{FIELD_SEP}two\n")


def test_log_options_to_args():
    opts = LogOptions(since="2026-01-01", until="2026-02-01", rev="dev",
                      paths=("src",), include_merges=False)
    assert opts.to_args() == [
        "--since=2026-01-01", "--until=2026-02-01", "--no-merges", "dev", "--", "src",
    ]
    assert LogOptions().to_args() == ["--"]


def test_read_commits_from_real_repo(history_repo: Path):
    commits = read_commits(history_repo)
    assert [c.subject for c in commits][:1] == ["Merge branch 'feature'"]
    assert len(commits) == 7
    assert commits[0].is_merge and commits[0].files == ()
    logo = next(c for c in commits if c.subject == "feat: add logo")
    assert logo.files[0].binary
    fix = next(c for c in commits if c.subject == "fix: app output")
    assert (fix.added, fix.deleted) == (1, 2)


def test_read_commits_filters(history_repo: Path):
    only_src = read_commits(history_repo, LogOptions(paths=("src",)))
    assert [c.subject for c in only_src] == ["fix: app output", "feat: add app"]
    recent = read_commits(history_repo, LogOptions(since="2026-03-02T00:00:00Z"))
    assert len(recent) == 4
    assert len(read_commits(history_repo, LogOptions(include_merges=False))) == 6
    feature = read_commits(history_repo, LogOptions(rev="main~1..feature"))
    assert [c.subject for c in feature] == ["fix: app output"]


def test_read_commits_keeps_unicode_paths_and_names(empty_repo: Path):
    commit(empty_repo, "docs/café notes.md", "x\n", "docs: ünïcode",
           author="Zoë <zoe@example.com>", date="2026-04-01T10:00:00+00:00")
    [c] = read_commits(empty_repo)
    assert c.author_name == "Zoë"
    assert c.files[0].path == "docs/café notes.md"


def test_read_commits_applies_mailmap(history_repo: Path):
    (history_repo / ".mailmap").write_text(
        "Robert <bob@example.com> <BOB@example.com>\n", encoding="utf-8"
    )
    fix = next(c for c in read_commits(history_repo) if c.subject == "fix: app output")
    assert (fix.author_name, fix.author_email) == ("Robert", "bob@example.com")


def test_read_commits_empty_repo(empty_repo: Path):
    assert read_commits(empty_repo) == []


def test_read_commits_bad_revision(history_repo: Path):
    with pytest.raises(GitError):
        read_commits(history_repo, LogOptions(rev="no-such-branch"))
