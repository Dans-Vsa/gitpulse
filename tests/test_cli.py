import csv
import io
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gitpulse import __version__, cli
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


def test_summary_author_and_path_filters(history_repo: Path):
    args = ["summary", str(history_repo), "--json"]
    alice = json.loads(runner.invoke(app, [*args, "--author", "alice"]).output)
    assert alice["commits"] == 4 and alice["authors"] == 1
    src = json.loads(runner.invoke(app, [*args, "--path", "src/"]).output)
    assert src["commits"] == 2 and src["files_touched"] == 1
    both = json.loads(runner.invoke(app, [*args, "-a", "alice", "-a", "bob"]).output)
    assert both["commits"] == 7


def test_authors_table(history_repo: Path):
    result = runner.invoke(app, ["authors", str(history_repo)])
    assert result.exit_code == 0, result.output
    assert "Alice" in result.output and "Bob" in result.output
    assert "57%" in result.output  # 4 of 7 commits
    assert "aka" in result.output and "bob@example.com" in result.output
    assert "example.com>" not in result.output  # emails hidden by default


def test_authors_table_with_emails(history_repo: Path, monkeypatch):
    # Widen the console so long emails are not wrapped mid-word.
    monkeypatch.setattr(cli.console, "width", 160)
    result = runner.invoke(app, ["authors", str(history_repo), "--emails"])
    assert result.exit_code == 0, result.output
    assert "<alice@example.com>" in result.output


def test_authors_json(history_repo: Path):
    result = runner.invoke(app, ["authors", str(history_repo), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["commits"] == 7
    assert data["total_authors"] == 2
    assert [a["name"] for a in data["authors"]] == ["Alice", "Bob"]
    assert data["authors"][1]["lines_deleted"] == 2


def test_authors_top_sort_and_filters(history_repo: Path):
    args = ["authors", str(history_repo), "--json"]
    top = json.loads(runner.invoke(app, [*args, "--top", "1", "--sort", "deleted"]).output)
    assert [a["name"] for a in top["authors"]] == ["Bob"]
    assert top["total_authors"] == 2 and top["sort"] == "deleted"
    src = json.loads(runner.invoke(app, [*args, "--path", "src/"]).output)
    assert [(a["name"], a["commits"]) for a in src["authors"]] == [("Bob", 2)]
    bob = json.loads(runner.invoke(app, [*args, "--author", "BOB"]).output)
    assert bob["total_authors"] == 1


def test_authors_top_note_in_table(history_repo: Path):
    result = runner.invoke(app, ["authors", str(history_repo), "-n", "1"])
    assert result.exit_code == 0, result.output
    assert "Showing 1 of 2 authors" in result.output


def test_authors_invalid_sort(history_repo: Path):
    result = runner.invoke(app, ["authors", str(history_repo), "--sort", "karma"])
    assert result.exit_code == 2
    assert "--sort must be one of" in result.output


def test_authors_empty_repo_and_outside_repo(empty_repo: Path, tmp_path: Path):
    empty = runner.invoke(app, ["authors", str(empty_repo)])
    assert empty.exit_code == 0 and "No commits found" in empty.output
    outside = runner.invoke(app, ["authors", str(tmp_path / "nowhere")])
    assert outside.exit_code == 1


def test_hotspots_table(history_repo: Path):
    result = runner.invoke(app, ["hotspots", str(history_repo)])
    assert result.exit_code == 0, result.output
    assert "hotspots (files)" in result.output
    assert "README.md" in result.output and "src/app.py" in result.output
    assert "(binary)" in result.output


def test_hotspots_json_files_and_dirs(history_repo: Path):
    args = ["hotspots", str(history_repo), "--json"]
    files = json.loads(runner.invoke(app, args).output)
    assert files["kind"] == "files" and files["total_files"] == 4
    assert files["hotspots"][0] == {**files["hotspots"][0], "path": "README.md", "churn": 6}
    dirs = json.loads(runner.invoke(app, [*args, "--depth", "1"]).output)
    assert dirs["kind"] == "directories"
    assert [h["path"] for h in dirs["hotspots"]] == [".", "src"]


def test_hotspots_top_sort_and_filters(history_repo: Path):
    args = ["hotspots", str(history_repo), "--json"]
    top = json.loads(runner.invoke(app, [*args, "-n", "1", "--sort", "last"]).output)
    assert [h["path"] for h in top["hotspots"]] == ["notes.txt"]
    bob = json.loads(runner.invoke(app, [*args, "--author", "bob"]).output)
    assert {h["path"] for h in bob["hotspots"]} == {"src/app.py", "logo.png"}
    src = json.loads(runner.invoke(app, [*args, "--path", "src/"]).output)
    assert [h["path"] for h in src["hotspots"]] == ["src/app.py"]


def test_hotspots_directory_table_and_top_note(history_repo: Path):
    result = runner.invoke(app, ["hotspots", str(history_repo), "-d", "1", "-n", "1"])
    assert result.exit_code == 0, result.output
    assert "Directory" in result.output
    assert "Showing 1 of 2 directories" in result.output


def test_hotspots_invalid_sort(history_repo: Path):
    bad = runner.invoke(app, ["hotspots", str(history_repo), "--sort", "size"])
    assert bad.exit_code == 2


def test_hotspots_empty_repo(empty_repo: Path):
    empty = runner.invoke(app, ["hotspots", str(empty_repo)])
    assert empty.exit_code == 0 and "No changes found" in empty.output


def test_heatmap_renders_both_views(history_repo: Path):
    result = runner.invoke(app, ["heatmap", str(history_repo)])
    assert result.exit_code == 0, result.output
    assert "Commits by weekday and hour (author local time)" in result.output
    assert "Daily commits" in result.output and "(7 commits)" in result.output
    assert "Busiest slot: Tue 11:00" in result.output
    assert "less" in result.output and "more" in result.output


def test_heatmap_single_views(history_repo: Path):
    hours = runner.invoke(app, ["heatmap", str(history_repo), "--view", "hours", "--utc"])
    assert "(UTC)" in hours.output and "Daily commits" not in hours.output
    cal = runner.invoke(app, ["heatmap", str(history_repo), "--view", "calendar", "-w", "4"])
    assert "Daily commits 2026-02-09" in cal.output and "weekday and hour" not in cal.output


def test_heatmap_json(history_repo: Path):
    result = runner.invoke(app, ["heatmap", str(history_repo), "--json", "--author", "alice"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["commits"] == 4
    assert data["weekdays"][0] == "Mon"
    assert sum(map(sum, data["hours"])) == 4
    assert data["days"] == {"2026-03-01": 1, "2026-03-03": 1, "2026-03-04": 1, "2026-03-05": 1}
    assert data["busiest"] == {"weekday": "Tue", "hour": 11, "commits": 1}


def test_heatmap_invalid_view(history_repo: Path):
    result = runner.invoke(app, ["heatmap", str(history_repo), "--view", "pie"])
    assert result.exit_code == 2


def test_heatmap_empty_repo(empty_repo: Path):
    result = runner.invoke(app, ["heatmap", str(empty_repo)])
    assert result.exit_code == 0 and "No commits found" in result.output
    data = json.loads(runner.invoke(app, ["heatmap", str(empty_repo), "--json"]).output)
    assert data["busiest"] is None and data["days"] == {}


@pytest.mark.parametrize("command", ["summary", "authors", "hotspots", "heatmap"])
def test_every_report_exports_csv_and_markdown(history_repo: Path, command: str):
    as_csv = runner.invoke(app, [command, str(history_repo), "--format", "csv"])
    assert as_csv.exit_code == 0, as_csv.output
    rows = list(csv.DictReader(io.StringIO(as_csv.output)))
    assert rows
    as_md = runner.invoke(app, [command, str(history_repo), "-f", "markdown"])
    assert as_md.exit_code == 0, as_md.output
    assert as_md.output.startswith(f"## gitpulse {command} - ")
    assert "|---|" in as_md.output


def test_format_json_matches_json_flag(history_repo: Path):
    a = runner.invoke(app, ["authors", str(history_repo), "--json"]).output
    b = runner.invoke(app, ["authors", str(history_repo), "--format", "JSON"]).output
    assert json.loads(a) == json.loads(b)


def test_csv_contents(history_repo: Path):
    out = runner.invoke(app, ["hotspots", str(history_repo), "-f", "csv"]).output
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows[0]["path"] == "README.md" and rows[0]["churn"] == "6"
    heat = runner.invoke(app, ["heatmap", str(history_repo), "-f", "csv"]).output
    heat_rows = list(csv.DictReader(io.StringIO(heat)))
    assert [r["weekday"] for r in heat_rows][:2] == ["Mon", "Tue"]
    assert sum(int(r["total"]) for r in heat_rows) == 7
    assert heat_rows[1]["11"] == "1"


def test_output_file_infers_format_from_suffix(history_repo: Path, tmp_path: Path):
    target = tmp_path / "reports" / "authors.csv"
    result = runner.invoke(app, ["authors", str(history_repo), "--output", str(target)])
    assert result.exit_code == 0, result.output
    assert "Wrote csv report" in result.output
    assert target.read_text(encoding="utf-8").startswith("name,email,aliases,commits")


def test_output_file_with_explicit_format(history_repo: Path, tmp_path: Path):
    target = tmp_path / "summary.txt"
    result = runner.invoke(app, ["summary", str(history_repo), "-f", "json", "-o", str(target)])
    assert result.exit_code == 0, result.output
    assert json.loads(target.read_text(encoding="utf-8"))["commits"] == 7


def test_output_file_unknown_suffix_and_bad_format(history_repo: Path, tmp_path: Path):
    unknown = runner.invoke(app, ["summary", str(history_repo), "-o", str(tmp_path / "s.txt")])
    assert unknown.exit_code == 2 and "cannot tell the format" in unknown.output
    bad = runner.invoke(app, ["summary", str(history_repo), "--format", "xml"])
    assert bad.exit_code == 2 and "--format must be one of" in bad.output
