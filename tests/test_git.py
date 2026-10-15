from datetime import datetime
from pathlib import Path

import pytest

from gitpulse.git import GitError, find_repo_root, git_version, repo_info, run_git


def test_git_version_looks_like_a_version():
    assert git_version()[0].isdigit()


def test_find_repo_root_from_subdirectory(sample_repo: Path):
    assert find_repo_root(sample_repo / "src") == sample_repo.resolve()


def test_find_repo_root_from_file(sample_repo: Path):
    assert find_repo_root(sample_repo / "src" / "app.py") == sample_repo.resolve()


def test_find_repo_root_outside_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(GitError, match="not a git repository"):
        find_repo_root(plain)


def test_find_repo_root_missing_path(tmp_path: Path):
    with pytest.raises(GitError, match="does not exist"):
        find_repo_root(tmp_path / "nope")


def test_run_git_raises_with_stderr(sample_repo: Path):
    with pytest.raises(GitError, match="unknown revision|bad revision|ambiguous"):
        run_git(["log", "no-such-branch"], cwd=sample_repo)


def test_repo_info_for_sample_repo(sample_repo: Path):
    info = repo_info(sample_repo)
    assert info.root == sample_repo.resolve()
    assert info.branch == "main"
    assert info.commit_count == 3
    assert info.first_commit == datetime.fromisoformat("2026-01-05T09:00:00+07:00")
    assert info.last_commit == datetime.fromisoformat("2026-02-01T20:15:00+07:00")
    assert info.remote_url is None


def test_repo_info_for_empty_repo(empty_repo: Path):
    info = repo_info(empty_repo)
    assert info.commit_count == 0
    assert info.first_commit is None and info.last_commit is None
    assert info.branch == "main"


def test_repo_info_reads_remote(sample_repo: Path):
    run_git(["remote", "add", "origin", "https://example.com/demo.git"], cwd=sample_repo)
    assert repo_info(sample_repo).remote_url == "https://example.com/demo.git"
