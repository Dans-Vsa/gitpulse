"""Read commit history by running ``git log --numstat`` and parsing its output.

The log is requested with ASCII control characters as separators so commit
subjects, author names and paths can contain any printable text:

    \\x1e  starts a new commit record
    \\x1f  separates header fields

Renames are disabled (``--no-renames``), so a moved file shows up as one
deletion plus one addition. That keeps per-path churn simple and exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gitpulse.git import GitError, parse_git_date, run_git
from gitpulse.models import Commit, FileChange

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"
# sha, parents, author name + email (%aN/%aE respect .mailmap),
# author date (strict ISO 8601), subject
LOG_FORMAT = RECORD_SEP + FIELD_SEP.join(["%H", "%P", "%aN", "%aE", "%aI", "%s"])
HEADER_FIELDS = 6


@dataclass(frozen=True, slots=True)
class LogOptions:
    """Filters passed through to ``git log``."""

    since: str | None = None
    until: str | None = None
    rev: str | None = None
    paths: tuple[str, ...] = ()
    include_merges: bool = True

    def to_args(self) -> list[str]:
        args: list[str] = []
        if self.since:
            args.append(f"--since={self.since}")
        if self.until:
            args.append(f"--until={self.until}")
        if not self.include_merges:
            args.append("--no-merges")
        if self.rev:
            args.append(self.rev)
        args.append("--")
        args.extend(self.paths)
        return args


def parse_numstat(line: str) -> FileChange | None:
    """Parse one ``added<TAB>deleted<TAB>path`` line; ``-`` counts mean binary."""
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    added, deleted, path = parts
    if added == "-" and deleted == "-":
        return FileChange(path=path, added=0, deleted=0, binary=True)
    try:
        return FileChange(path=path, added=int(added), deleted=int(deleted))
    except ValueError:
        return None


def parse_log(raw: str) -> list[Commit]:
    """Parse ``git log`` output produced with ``LOG_FORMAT`` and ``--numstat``."""
    commits: list[Commit] = []
    for record in raw.split(RECORD_SEP):
        if not record.strip():
            continue
        header, _, body = record.partition("\n")
        fields = header.split(FIELD_SEP)
        if len(fields) != HEADER_FIELDS:
            raise GitError(f"unexpected git log record: {header[:80]!r}")
        sha, parents, name, email, date, subject = fields
        files = tuple(
            change
            for line in body.splitlines()
            if line.strip() and (change := parse_numstat(line)) is not None
        )
        commits.append(
            Commit(
                sha=sha,
                author_name=name,
                author_email=email,
                authored_at=parse_git_date(date),
                subject=subject,
                parents=tuple(parents.split()),
                files=files,
            )
        )
    return commits


def has_commits(repo: Path) -> bool:
    try:
        run_git(["rev-parse", "--verify", "--quiet", "HEAD"], cwd=repo)
    except GitError:
        return False
    return True


def read_commits(repo: Path, options: LogOptions | None = None) -> list[Commit]:
    """Return the commits (newest first) of the repository at ``repo``.

    Author names and emails go through ``.mailmap`` when the repo has one.
    """
    options = options or LogOptions()
    if not has_commits(repo):
        return []
    args = [
        "-c",
        "core.quotepath=off",
        "log",
        f"--pretty=format:{LOG_FORMAT}",
        "--numstat",
        "--no-renames",
        "--use-mailmap",
        *options.to_args(),
    ]
    return parse_log(run_git(args, cwd=repo))
