"""Filters applied to parsed commits after they come back from ``git log``.

Path filtering is delegated to git (pathspecs in ``LogOptions.paths``) because
git also limits the ``--numstat`` lines to those paths. Author filtering is done
here so it sees the identities *after* ``.mailmap`` has been applied.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from gitpulse.models import Commit


def matches_author(commit: Commit, patterns: Sequence[str]) -> bool:
    """True if any pattern is a case-insensitive substring of the name or email."""
    identity = f"{commit.author_name} <{commit.author_email}>".lower()
    return any(p.strip().lower() in identity for p in patterns if p.strip())


def filter_by_author(commits: Iterable[Commit], patterns: Sequence[str] | None) -> list[Commit]:
    """Keep commits whose author matches at least one pattern (no patterns: keep all)."""
    commits = list(commits)
    if not patterns or not any(p.strip() for p in patterns):
        return commits
    return [c for c in commits if matches_author(c, patterns)]
