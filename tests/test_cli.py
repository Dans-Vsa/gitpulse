import json
from pathlib import Path

from typer.testing import CliRunner

from gitpulse import __version__
from gitpulse.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "doctor" in result.output


def test_doctor_on_sample_repo(sample_repo: Path):
    result = runner.invoke(app, ["doctor", str(sample_repo)])
    assert result.exit_code == 0, result.output
    assert "commits" in result.output
    assert "3" in result.output
    assert "2026-01-05" in result.output
    assert "Ready." in result.output


def test_doctor_on_empty_repo(empty_repo: Path):
    result = runner.invoke(app, ["doctor", str(empty_repo)])
    assert result.exit_code == 0, result.output
    assert "No commits yet" in result.output


def test_doctor_outside_repo(tmp_path: Path):
    result = runner.invoke(app, ["doctor", str(tmp_path)])
    assert result.exit_code == 1
    assert "not a git repository" in result.output


def test_summary_table(history_repo: Path):
    result = runner.invoke(app, ["summary", str(history_repo)])
    assert result.exit_code == 0, result.output
    assert "Commits" in result.output
    assert "7 (1 merges)" in result.output
    assert "+9" in result.output
    assert "2026-03-01" in result.output


def test_summary_json(history_repo: Path):
    result = runner.invoke(app, ["summary", str(history_repo), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["commits"] == 7
    assert data["authors"] == 2
    assert data["net_lines"] == 6
    assert data["repository"] == str(history_repo.resolve())


def test_summary_filters(history_repo: Path):
    args = ["summary", str(history_repo), "--json"]
    since = json.loads(runner.invoke(app, [*args, "--since", "2026-03-02T00:00:00Z"]).output)
    assert since["commits"] == 4
    until = json.loads(runner.invoke(app, [*args, "--until", "2026-03-02T00:00:00Z"]).output)
    assert until["commits"] == 3
    no_merges = json.loads(runner.invoke(app, [*args, "--no-merges"]).output)
    assert no_merges["merges"] == 0 and no_merges["commits"] == 6
    feature = json.loads(runner.invoke(app, [*args, "--rev", "main~1..feature"]).output)
    assert feature["commits"] == 1


def test_summary_empty_repo(empty_repo: Path):
    result = runner.invoke(app, ["summary", str(empty_repo)])
    assert result.exit_code == 0
    assert "No commits found" in result.output


def test_summary_outside_repo(tmp_path: Path):
    result = runner.invoke(app, ["summary", str(tmp_path)])
    assert result.exit_code == 1
    assert "not a git repository" in result.output


def test_summary_bad_revision(history_repo: Path):
    result = runner.invoke(app, ["summary", str(history_repo), "--rev", "nope"])
    assert result.exit_code == 1
    assert "error" in result.output
