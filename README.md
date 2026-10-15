# gitpulse

**Terminal analytics for git repositories** — see who works on what, which files churn the most, and when a project is most active, without leaving the command line.

`gitpulse` wraps the `git` executable you already have, parses its history, and renders the results as rich terminal tables and heatmaps. No server, no account, no API keys.

> Status: early development (v0.1.0). The roadmap below shows what works today.

## Features

- [x] `gitpulse doctor` — verify git is installed and show repository facts (root, branch, commit count, first/last commit, remote)
- [x] `gitpulse --version`
- [ ] `gitpulse summary` — commits, contributors, lines added/removed, active days for a date range
- [ ] `gitpulse authors` — per-contributor stats with mailmap-style alias merging
- [ ] `gitpulse hotspots` — most-changed files and directories (churn), filterable by path
- [ ] `gitpulse heatmap` — weekday × hour activity grid and a GitHub-style calendar
- [ ] Export any report as JSON, CSV or Markdown
- [ ] Shared filters: `--since`, `--until`, `--author`, `--path`

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
```

Example output:

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
│   └── git.py          # git subprocess wrapper, repo discovery, repo info
├── tests/
│   ├── conftest.py     # temporary repo fixtures
│   ├── test_cli.py
│   └── test_git.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

[MIT](LICENSE) © Dans-Vsa
