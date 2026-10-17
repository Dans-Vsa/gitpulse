import csv
import io
import json
from pathlib import Path

import pytest

from gitpulse.export import guess_format, render, to_csv, to_json, to_markdown

COLUMNS = ["path", "churn", "binary", "share", "aliases", "last"]
ROWS = [
    {"path": "a|b.py", "churn": 10, "binary": False, "share": 0.5, "aliases": ["x", "y"],
     "last": None},
    {"path": "logo.png", "churn": 0, "binary": True, "share": 0.3333333, "aliases": []},
]


def test_to_json_keeps_unicode():
    assert json.loads(to_json({"name": "Dédé"})) == {"name": "Dédé"}
    assert "Dédé" in to_json({"name": "Dédé"})


def test_to_csv_round_trips():
    text = to_csv(COLUMNS, ROWS)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0] == {"path": "a|b.py", "churn": "10", "binary": "false", "share": "0.5",
                       "aliases": "x; y", "last": ""}
    assert rows[1]["binary"] == "true"
    assert rows[1]["share"] == "0.3333"
    assert rows[1]["last"] == ""  # missing keys become empty cells


def test_to_markdown_escapes_pipes():
    text = to_markdown(COLUMNS, ROWS, title="Hotspots")
    lines = text.splitlines()
    assert lines[0] == "## Hotspots"
    assert lines[2] == "| path | churn | binary | share | aliases | last |"
    assert lines[3] == "|---|---|---|---|---|---|"
    assert lines[4] == "| a\\|b.py | 10 | false | 0.5 | x; y |  |"
    assert len(lines) == 6


def test_render_dispatches_and_rejects_unknown():
    assert render("json", {"a": 1}, [], []) == to_json({"a": 1})
    assert render("csv", {}, COLUMNS, ROWS) == to_csv(COLUMNS, ROWS)
    assert render("markdown", {}, COLUMNS, ROWS).startswith("| path")
    with pytest.raises(ValueError):
        render("xml", {}, COLUMNS, ROWS)


@pytest.mark.parametrize(
    ("name", "expected"),
    [("r.json", "json"), ("r.CSV", "csv"), ("r.md", "markdown"), ("r.markdown", "markdown"),
     ("r.txt", None), ("report", None)],
)
def test_guess_format(name, expected):
    assert guess_format(Path(name)) == expected
    assert guess_format(None) is None
