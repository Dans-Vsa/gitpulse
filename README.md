# gitpulse

**Terminal analytics for git repositories** — see who works on what, which files churn the most, and when a project is most active, without leaving the command line.

`gitpulse` wraps the `git` executable you already have, parses its history, and renders the results as rich terminal tables and heatmaps. No server, no account, no API keys.

> Status: early development (v0.2.0). The roadmap below shows what works today.

## Features

- [x] `gitpulse doctor` — verify git is installed and show repository facts (root, branch, commit count, first/last commit, remote)
- [x] `gitpulse --version`
- [x] `gitpulse summary` — commits, merges, authors, lines added/removed, active days, busiest day and top author, as a table or `--json`
- [x] Robust history parser (`git log --numstat` with control-character separators): handles binary files, merges, Unicode names/paths and `.mailmap`
- [ ] `gitpulse authors` — per-contributor stats with mailmap-style alias merging
- [ ] `gitpulse hotspots` — most-changed files and directories (churn), filterable by path
- [ ] `gitpulse heatmap` — weekday × hour activity grid and a GitHub-style calendar
- [ ] Export any report as JSON, CSV or Markdown
- [x] History filters: `--since`, `--until`, `--rev` (branch, tag or range), `--no-merges`
- [ ] More filters: `--author`, `--path`, `--top`

## Tech stack

| Area      | Choice                                      |
|-----------|---------------------------------------------|
| Language  | Python 3.10+                                |
| CLI       | [Typer](https://typer.tiangolo.com/)        |
| Output    | [Rich](https://rich.readthedocs.io/)        |
| Data      | the local `git` binary (via `subprocess`)   |
| Tests     | pytest, with throwaway git repos as fixtures |

## Installation

Requires Python 3.10+ and git on your `PATH`.

```bash
git clone https://github.com/Dans-Vsa/gitpulse.git
cd gitpulse
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
gitpulse --version
gitpulse doctor              # current directory
gitpulse doctor path/to/repo # any path inside a repository
python -m gitpulse doctor    # same thing without the console script

gitpulse summary                                  # whole history of HEAD
gitpulse summary path/to/repo --since "3 months ago"
gitpulse summary --since 2026-01-01 --until 2026-07-01 --no-merges
gitpulse summary --rev main..feature              # only commits on a branch
gitpulse summary --json > summary.json            # machine-readable
```

### `gitpulse summary`

```
gitpulse · spendwise-api
┌──────────────────────┬─────────────────────────┐
│ Commits              │           32 (0 merges) │
│ Authors              │                       1 │
│ First commit         │              2026-10-08 │
│ Last commit          │              2026-10-15 │
│ Active days          │                  8 of 8 │
│ Commits / active day │                    4.00 │
│ Lines                │ +4,750 -88 (net +4,662) │
│ Files touched        │                      66 │
│ Busiest day          │  2026-10-14 (8 commits) │
│ Top author           │   Dans-Vsa (32 commits) │
└──────────────────────┴─────────────────────────┘
```

Notes:

- Authors are counted by email, case-insensitively, after applying the repository's `.mailmap`.
- Renames are not followed: a moved file counts as one deletion plus one addition.
- Binary files are listed as touched but add no line counts.

### `gitpulse doctor`

```
git           2.51.1.windows.1
repository    C:\code\my-project
branch        main
commits       128
first commit  2026-03-02 10:14 +0700
last commit   2026-10-15 09:41 +0700
remote        https://github.com/me/my-project.git
Ready.
```

## Running tests

```bash
pytest
```

The test suite builds small git repositories in temporary folders with fixed authors and timestamps, so results are deterministic.

## Project structure

```
gitpulse/
├── src/gitpulse/
│   ├── __init__.py     # package version
│   ├── __main__.py     # `python -m gitpulse`
│   ├── cli.py          # Typer app and commands
│   ├── git.py          # git subprocess wrapper, repo discovery, repo info
│   ├── history.py      # `git log --numstat` runner/parser and LogOptions filters
│   ├── models.py       # Commit / FileChange dataclasses
│   └── stats.py        # Summary aggregation
├── tests/
│   ├── conftest.py     # temporary repo fixtures (incl. a branch + merge history)
│   ├── test_cli.py
│   ├── test_git.py
│   ├── test_history.py
│   └── test_stats.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

[MIT](LICENSE) © Dans-Vsa
