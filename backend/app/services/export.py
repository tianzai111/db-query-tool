"""Data export service.

This module is the core of the "data export feature module" added on top of the
existing intelligent database query tool. It converts a ``QueryResult`` (which is
already produced by the query execution pipeline) into a downloadable file in
one of the supported formats:

* **CSV** -- RFC 4180 compliant, UTF-8 with BOM so that Microsoft Excel opens
  Chinese / Unicode content correctly.
* **JSON** -- structured payload that carries both the result data and metadata
  (column definitions, row count, execution time, the SQL that produced the
  data and a generation timestamp).

The service is deliberately *pure*: it receives the in-memory ``QueryResult``
and returns the serialised byte payload plus a suggested filename. This keeps
it easy to unit-test and allows the same logic to be reused both by the REST
endpoint (``/api/v1/dbs/{name}/export``) and by AI-agent / CLI automation.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.models.schemas import QueryColumn, QueryResult


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"

    @classmethod
    def from_string(cls, value: str) -> "ExportFormat":
        """Parse a format string case-insensitively.

        Args:
            value: Format name such as ``"csv"`` or ``"JSON"``.

        Returns:
            The matching ``ExportFormat`` member.

        Raises:
            ValueError: If the format is not supported.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        supported = ", ".join(m.value for m in cls)
        raise ValueError(
            f"Unsupported export format: '{value}'. Supported formats: {supported}"
        )

    @property
    def media_type(self) -> str:
        """Return the MIME type used in the HTTP ``Content-Type`` header."""
        if self is ExportFormat.CSV:
            # charset=utf-8 is declared explicitly; we also write a BOM.
            return "text/csv; charset=utf-8"
        return "application/json; charset=utf-8"

    @property
    def file_extension(self) -> str:
        """Return the canonical file extension (without the dot)."""
        return self.value


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _json_safe(value: Any) -> Any:
    """Convert a value into something ``json.dumps`` can always serialise.

    Database drivers may return ``datetime``/``date``/``Decimal``/``UUID`` etc.
    We normalise them to string representations so that the JSON export never
    raises ``TypeError``.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        # Always emit ISO-8601 UTC for deterministic output.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    # date, Decimal, UUID, bytes, ... -> string
    return str(value)


def _rows_as_dicts(
    columns: list[QueryColumn], rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return rows ordered exactly by ``columns`` and with JSON-safe values."""
    col_names = [c.name for c in columns]
    safe_rows: list[dict[str, Any]] = []
    for row in rows:
        safe_rows.append(
            {name: _json_safe(row.get(name)) for name in col_names}
        )
    return safe_rows


def _to_csv(result: QueryResult) -> bytes:
    """Serialise a ``QueryResult`` to CSV bytes (UTF-8 with BOM)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(
        buffer,
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",  # RFC 4180 line endings, Excel-friendly
    )

    # Header row
    writer.writerow([col.name for col in result.columns])

    # Data rows -- follow the column order so the file matches the on-screen
    # table even if individual row dicts have extra / differently ordered keys.
    col_names = [c.name for c in result.columns]
    for row in result.rows:
        writer.writerow([_json_safe(row.get(name)) for name in col_names])

    # Prepend UTF-8 BOM so Excel auto-detects encoding.
    return "\ufeff".encode("utf-8") + buffer.getvalue().encode("utf-8")


def _to_json(result: QueryResult, database_name: str | None = None) -> bytes:
    """Serialise a ``QueryResult`` to a structured JSON document."""
    payload: dict[str, Any] = {
        "metadata": {
            "database": database_name,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "rowCount": result.row_count,
            "executionTimeMs": result.execution_time_ms,
            "sql": result.sql,
            "columns": [
                {"name": col.name, "dataType": col.data_type}
                for col in result.columns
            ],
        },
        "rows": _rows_as_dicts(result.columns, result.rows),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_filename(
    database_name: str, fmt: ExportFormat, timestamp: datetime | None = None
) -> str:
    """Build a deterministic, human-readable export filename.

    Example: ``mydb_query_20260422T103000.csv``
    """
    ts = timestamp or datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in database_name)
    return f"{safe_name}_query_{stamp}.{fmt.file_extension}"


def export_result(
    result: QueryResult,
    fmt: ExportFormat,
    database_name: str | None = None,
) -> tuple[bytes, str]:
    """Convert a query result into an exportable byte payload.

    Args:
        result: The query result to export.
        fmt: Desired output format.
        database_name: Optional database name, included in JSON metadata and
            used to build the suggested filename.

    Returns:
        A tuple ``(content_bytes, suggested_filename)``.
    """
    if fmt is ExportFormat.CSV:
        content = _to_csv(result)
    elif fmt is ExportFormat.JSON:
        content = _to_json(result, database_name=database_name)
    else:  # pragma: no cover - guarded by enum
        raise ValueError(f"Unsupported export format: {fmt}")

    filename = build_filename(database_name or "export", fmt)
    return content, filename
