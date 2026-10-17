# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-10-17

### Fixed
- Python 3.10: commits made in UTC crashed the history parser because git prints
  their dates with a `Z` suffix, which `datetime.fromisoformat` only accepts from
  Python 3.11. Found by the new CI matrix.

## [1.0.0] - 2026-10-17

### Added
- `--format table|json|csv|markdown` and `--output FILE` on `summary`, `authors`,
  `hotspots` and `heatmap`; the format is inferred from `.json`, `.csv` or `.md`.
- GitHub Actions CI running the test suite on Linux and Windows, Python 3.10–3.13.
- This changelog.

### Changed
- `--json` is now a shortcut for `--format json`.

## [0.5.0] - 2026-10-17

### Added
- `gitpulse heatmap`: weekday × hour grid and a GitHub-style calendar with
  `--view`, `--weeks`, `--utc` and `--json`.

## [0.4.0] - 2026-10-17

### Added
- `gitpulse hotspots`: churn per file, or per directory with `--depth N`, with
  `--sort`, `--top` and `--json`.

## [0.3.0] - 2026-10-17

### Added
- `gitpulse authors`: per-contributor stats with alias merging by email.
- Shared filters `--author` and `--path` (also on `summary`), plus `--top`.

## [0.2.0] - 2026-10-16

### Added
- History parser based on `git log --numstat` (binary files, merges, Unicode, `.mailmap`).
- `gitpulse summary` with `--since`, `--until`, `--rev`, `--no-merges` and `--json`.

## [0.1.0] - 2026-10-15

### Added
- Project scaffold, git wrapper, `gitpulse doctor` and `--version`.

[1.0.1]: https://github.com/Dans-Vsa/gitpulse/releases/tag/v1.0.1
[1.0.0]: https://github.com/Dans-Vsa/gitpulse/releases/tag/v1.0.0
