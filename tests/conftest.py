"""Shared fixtures: throwaway git repositories with deterministic history."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    ).stdout


def commit(repo: Path, filename: str, content: str, message: str, *, author: str, date: str) -> None:
    """Write a file and commit it with a fixed author and timestamp."""
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content, encoding="utf-8")
    name, email = author.split(" <")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email.rstrip(">"),
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email.rstrip(">"),
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    git(repo, "add", filename)
    git(repo, "commit", "-q", "-m", message, env=env)


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "empty"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    return repo


@pytest.fixture
def sample_repo(empty_repo: Path) -> Path:
    """A small repo with three commits by two authors."""
    repo = empty_repo
    commit(repo, "README.md", "# demo\n", "docs: add readme",
           author="Alice <alice@example.com>", date="2026-01-05T09:00:00+07:00")
    commit(repo, "src/app.py", "print('hi')\n", "feat: add app",
           author="Bob <bob@example.com>", date="2026-01-06T14:30:00+07:00")
    commit(repo, "src/app.py", "print('hello')\n", "fix: greeting",
           author="Alice <alice@example.com>", date="2026-02-01T20:15:00+07:00")
    return repo
