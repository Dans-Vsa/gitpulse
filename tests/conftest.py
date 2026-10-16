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


def author_env(author: str, date: str) -> dict[str, str]:
    """Environment that pins author/committer identity and timestamps."""
    name, email = author.split(" <")
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email.rstrip(">"),
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email.rstrip(">"),
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }


def commit(
    repo: Path, filename: str, content: str | bytes, message: str, *, author: str, date: str
) -> None:
    """Write a file (text or binary) and commit it with a fixed author and timestamp."""
    target = repo / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_bytes(content.encode("utf-8"))
    git(repo, "add", filename)
    git(repo, "commit", "-q", "-m", message, env=author_env(author, date))


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "empty"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.autocrlf", "false")
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


@pytest.fixture
def history_repo(empty_repo: Path) -> Path:
    """Richer history for the parser: a binary file, a case-variant email and a merge.

    Lines: README +3, app +2, README +2/-1, app +1/-2, notes +1  ->  +9 / -3.
    """
    repo = empty_repo
    alice = "Alice <alice@example.com>"
    bob = "Bob <bob@example.com>"
    commit(repo, "README.md", "a\nb\nc\n", "init: add readme",
           author=alice, date="2026-03-01T09:00:00+00:00")
    commit(repo, "src/app.py", "print('hi')\nprint('bye')\n", "feat: add app",
           author=bob, date="2026-03-01T15:30:00+00:00")
    commit(repo, "logo.png", b"\x89PNG\x00\x01\x02", "feat: add logo",
           author=bob, date="2026-03-01T16:00:00+00:00")
    commit(repo, "README.md", "a\nB\nc\nd\n", "docs: tweak readme",
           author=alice, date="2026-03-03T11:00:00+00:00")

    git(repo, "checkout", "-q", "-b", "feature")
    commit(repo, "src/app.py", "print('hello')\n", "fix: app output",
           author="Bob <BOB@example.com>", date="2026-03-04T20:00:00+00:00")
    git(repo, "checkout", "-q", "main")
    commit(repo, "notes.txt", "todo\n", "chore: notes",
           author=alice, date="2026-03-04T21:00:00+00:00")
    git(repo, "merge", "-q", "--no-ff", "feature", "-m", "Merge branch 'feature'",
        env=author_env(alice, "2026-03-05T08:00:00+00:00"))
    return repo
