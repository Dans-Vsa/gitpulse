"""Plain data structures shared by the history parser and the analytics code."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FileChange:
    """Line counts for one file in one commit (from ``git log --numstat``)."""

    path: str
    added: int
    deleted: int
    binary: bool = False

    @property
    def churn(self) -> int:
        return self.added + self.deleted


@dataclass(frozen=True, slots=True)
class Commit:
    """One commit with its author, timestamp and per-file line counts."""

    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    subject: str
    parents: tuple[str, ...] = ()
    files: tuple[FileChange, ...] = field(default_factory=tuple)

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

    @property
    def added(self) -> int:
        return sum(f.added for f in self.files)

    @property
    def deleted(self) -> int:
        return sum(f.deleted for f in self.files)
