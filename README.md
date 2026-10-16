# gitpulse

**Terminal analytics for git repositories** — see who works on what, which files churn the most, and when a project is most active, without leaving the command line.

`gitpulse` wraps the `git` executable you already have, parses its history, and renders the results as rich terminal tables and heatmaps. No server, no account, no API keys.

> Status: early development (v0.4.0). The roadmap below shows what works today.

## Features

- [x] `gitpulse doctor` — verify git is installed and show repository facts (root, branch, commit count, first/last commit, remote)
- [x] `gitpulse --version`
- [x] `gitpulse summary` — commits, merges, authors, lines added/removed, active days, busiest day and top author, as a table or `--json`
- [x] Robust history parser (`git log --numstat` with control-character separators): handles binary files, merges, Unicode names/paths and `.mailmap`
- [x] `gitpulse authors` — per-contributor commits, share, lines, files, active days and first/last commit; identities merged by email (case-insensitive) after `.mailmap`, with aliases shown; `--sort`, `--top`, `--emails`, `--json`
- [x] `gitpulse hotspots` — most-changed files, or directories with `--depth N`, ranked by churn (lines added + deleted) with commits, authors and last change; `--sort`, `--top`, `--json`
- [ ] `gitpulse heatmap` — weekday × hour activity grid and a GitHub-style calendar
- [ ] Export any report as JSON, CSV or Markdown
- [x] History filters: `--since`, `--until`, `--rev` (branch, tag or range), `--no-merges`
- [x] More filters: `--author` (name/email substring, repeatable), `--path` (git pathspec, repeatable), `--top`

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
gitpulse summary --author alice --path src/       # one person, one folder

gitpulse authors                                  # everyone, most commits first
gitpulse authors --top 5 --sort lines             # top 5 by lines changed
gitpulse authors --since "6 months ago" --emails  # recent contributors with emails
gitpulse authors --path docs/ -a bob -a carol     # who touched docs/, two people
gitpulse authors --json > authors.json

gitpulse hotspots                                 # top 20 files by churn
gitpulse hotspots --depth 1                       # roll up to top-level folders
gitpulse hotspots -d 2 --sort commits -n 10       # second-level folders by commit count
gitpulse hotspots --path src/ --since "90 days ago"
```

### `gitpulse hotspots`

Output for this project's sibling repo `spendwise-api`:

```
gitpulse · hotspots (files) · spendwise-api
#  File                     Churn          Commits  Authors        Last
────────────────────────────────────────────────────────────────────────
1  README.md                  465  ██████        9        1  2026-10-15
2  tests/test_budgets.py      247  ███           2        1  2026-10-14
3  tests/test_csv.py          235  ███           1        1  2026-10-14
4  app/api/transactions.py    196  ███           2        1  2026-10-14
5  app/services/csv_io.py     191  ██            1        1  2026-10-14
Showing 5 of 66 files (--top).
```

- **Churn** = lines added + lines deleted. Files that are both big-churn and touched by many commits are usually the riskiest code to change.
- `--depth N` groups files by their first N folders (`.` is the repository root); a commit that edits several files in one folder counts once for that folder.
- `--sort` accepts `churn` (default), `commits`, `added`, `deleted`, `authors`, `last`, `path`.
- Binary files are marked `(binary)`; they count as commits but add no churn.
- `--json` adds `lines_added` / `lines_deleted` for every row.

### `gitpulse authors`

```
gitpulse · authors · my-project
#  Author        Commits    %       +      -  Files  Days       First        Last
──────────────────────────────────────────────────────────────────────────────────
1  Alice              84  62%  12,410  3,902    143    51  2026-03-02  2026-10-15
   aka alice@old-laptop.local
2  Bob                41  30%   5,077  1,236     88    27  2026-04-11  2026-10-14
3  Carol              11   8%     690    214     19     9  2026-08-20  2026-10-01
```

- `--sort` accepts `commits` (default), `lines`, `added`, `deleted`, `files`, `first`, `last`, `name`.
- Commits from the same email (ignoring case) are merged into one person; other names/emails used by that person are listed as `aka …`. For anything else, add a [`.mailmap`](https://git-scm.com/docs/gitmailmap) file to the repository — gitpulse respects it.
- `--json` includes every author's aliases, share (0–1) and ISO 8601 first/last commit timestamps.

### Filters (all report commands)

| Option | Meaning |
|--------|---------|
| `--since`, `--until` | Date bounds, anything git understands (`2026-01-01`, `"2 weeks ago"`) |
| `--rev` | Branch, tag or range such as `main..feature` (default `HEAD`) |
| `--author`, `-a` | Author name or email contains this text, case-insensitive; repeat to OR |
| `--path`, `-p` | Limit to a path or pathspec (`src/`, `'*.py'`); line counts only cover those paths |
| `--no-merges` | Skip merge commits |
| `--json` | Machine-readable output |

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
│   ├── authors.py      # per-author aggregation, alias merging, sorting
│   ├── __main__.py     # `python -m gitpulse`
│   ├── cli.py          # Typer app, commands and shared filter options
│   ├── filters.py      # post-parse filters (author matching)
│   ├── git.py          # git subprocess wrapper, repo discovery, repo info
│   ├── history.py      # `git log --numstat` runner/parser and LogOptions filters
│   ├── hotspots.py     # per-file / per-directory churn aggregation
│   ├── models.py       # Commit / FileChange dataclasses
│   └── stats.py        # Summary aggregation
├── tests/
│   ├── conftest.py     # temporary repo fixtures (incl. a branch + merge history)
│   ├── test_authors.py
│   ├── test_cli.py
│   ├── test_filters.py
│   ├── test_git.py
│   ├── test_history.py
│   ├── test_hotspots.py
│   └── test_stats.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

[MIT](LICENSE) © Dans-Vsa
