"""Unit tests for the data export service."""
import csv
import io
import json

import pytest

from app.models.schemas import QueryColumn, QueryResult
from app.services.export import ExportFormat, build_filename, export_result


def _make_result() -> QueryResult:
    return QueryResult(
        columns=[
            QueryColumn(name="id", data_type="integer"),
            QueryColumn(name="name", data_type="character varying"),
            QueryColumn(name="active", data_type="boolean"),
        ],
        rows=[
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob, Jr.", "active": False},
            {"id": 3, "name": None, "active": None},
        ],
        rowCount=3,
        executionTimeMs=12,
        sql="SELECT id, name, active FROM users",
    )


def test_export_format_from_string_is_case_insensitive():
    assert ExportFormat.from_string("CSV") is ExportFormat.CSV
    assert ExportFormat.from_string("Json") is ExportFormat.JSON


def test_export_format_from_string_rejects_unknown():
    with pytest.raises(ValueError):
        ExportFormat.from_string("xml")


def test_export_csv_starts_with_bom_and_has_header():
    content, filename = export_result(_make_result(), ExportFormat.CSV, database_name="demo")
    assert filename.endswith(".csv")
    # BOM prefix for Excel Unicode detection
    assert content.startswith("\ufeff".encode("utf-8"))
    text = content.decode("utf-8-sig")
    reader = list(csv.reader(io.StringIO(text)))
    assert reader[0] == ["id", "name", "active"]
    assert reader[1] == ["1", "Alice", "True"]
    # Comma inside value must be quoted
    assert reader[2][1] == "Bob, Jr."
    # None renders as empty string
    assert reader[3][1] == ""


def test_export_json_contains_metadata_and_rows():
    content, filename = export_result(_make_result(), ExportFormat.JSON, database_name="demo")
    assert filename.endswith(".json")
    payload = json.loads(content.decode("utf-8"))
    assert payload["metadata"]["database"] == "demo"
    assert payload["metadata"]["rowCount"] == 3
    assert payload["metadata"]["sql"].startswith("SELECT")
    assert len(payload["metadata"]["columns"]) == 3
    assert payload["rows"][0] == {"id": 1, "name": "Alice", "active": True}
    assert payload["rows"][2]["name"] is None


def test_build_filename_is_deterministic():
    from datetime import datetime, timezone

    ts = datetime(2026, 4, 22, 10, 30, 0, tzinfo=timezone.utc)
    name = build_filename("my-db", ExportFormat.CSV, timestamp=ts)
    assert name == "my-db_query_20260422T103000Z.csv"
