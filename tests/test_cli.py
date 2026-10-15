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
