"""Turn report data into JSON, CSV or Markdown text.

Every report command builds two things: a nested JSON ``payload`` and a flat
list of ``rows`` (dicts) with an ordered list of ``columns``. JSON uses the
payload; CSV and Markdown use the rows, so spreadsheets and docs get one
clean table per report.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from pathlib import Path

FORMATS = ("table", "json", "csv", "markdown")
FILE_FORMATS = FORMATS[1:]
SUFFIX_FORMATS = {".json": "json", ".csv": "csv", ".md": "markdown", ".markdown": "markdown"}


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(v) for v in value)
    return str(value)


def to_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def to_csv(columns: Sequence[str], rows: Sequence[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row.get(c)) for c in columns])
    return buffer.getvalue()


def _md_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def to_markdown(columns: Sequence[str], rows: Sequence[dict], title: str | None = None) -> str:
    lines: list[str] = []
    if title:
        lines += [f"## {_md_escape(title)}", ""]
    lines.append("| " + " | ".join(_md_escape(c) for c in columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(_cell(row.get(c))) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def render(
    fmt: str,
    payload: dict,
    columns: Sequence[str],
    rows: Sequence[dict],
    title: str | None = None,
) -> str:
    """Render a report in one of ``FILE_FORMATS``."""
    if fmt == "json":
        return to_json(payload)
    if fmt == "csv":
        return to_csv(columns, rows)
    if fmt == "markdown":
        return to_markdown(columns, rows, title)
    raise ValueError(f"unknown export format {fmt!r}; choose from {', '.join(FILE_FORMATS)}")


def guess_format(output: Path | None) -> str | None:
    """Infer the format from an output file suffix (``.json``, ``.csv``, ``.md``)."""
    if output is None:
        return None
    return SUFFIX_FORMATS.get(output.suffix.lower())
