"""SQLite database adapter.

SQLite is bundled with Python and requires no external database server, which
makes it ideal for the zero-install demo environment. The standard-library
``sqlite3`` module is synchronous, so all database calls are run on a shared
asyncio thread executor to avoid blocking the FastAPI event loop.

A SQLite connection URL looks like:

    sqlite:///relative/path/demo.db
    sqlite:////absolute/path/demo.db
    sqlite:///:memory:
"""

import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.adapters.base import (
    ConnectionConfig,
    DatabaseAdapter,
    MetadataResult,
    QueryResult,
)

# Shared executor for all SQLite adapters. SQLite connections are not safe to
# share across threads unless check_same_thread=False, so each logical operation
# opens a short-lived connection against the same file.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sqlite")


def _database_path_from_url(url: str) -> str:
    """Extract a filesystem path from a ``sqlite:///...`` URL.

    ``sqlite:///foo.db``   -> ``foo.db`` (relative)
    ``sqlite:////tmp/x.db`` -> ``/tmp/x.db`` (absolute)
    ``sqlite:///:memory:`` -> ``:memory:``
    """
    parsed = urlparse(url)
    # netloc is empty for file URLs; path starts with '/'.
    path = parsed.path
    if path == "/:memory:":
        return ":memory:"
    # For an absolute path the URL is sqlite:////abs/path -> parsed.path = '/abs/path'
    # For a relative path it is sqlite:///rel/path -> parsed.path = '/rel/path'
    # We strip exactly one leading slash to restore the user-provided path.
    if path.startswith("/") and not path.startswith("//"):
        return path[1:]
    return path


def _connect(path: str) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _infer_type(value: Any) -> str:
    """Map a Python value to a human-readable column type name."""
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double precision"
    if isinstance(value, str):
        return "character varying"
    if isinstance(value, datetime):
        return "timestamp"
    return type(value).__name__


class SQLiteAdapter(DatabaseAdapter):
    """Synchronous sqlite3 driver wrapped in an async thread executor."""

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._db_path = _database_path_from_url(config.url)

    # -- connection management --------------------------------------------

    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Verify the database file is openable and run a trivial query."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                _EXECUTOR, self._test_connection_sync
            )
            return True, None
        except Exception as e:  # pragma: no cover - defensive
            return False, str(e)

    def _test_connection_sync(self) -> None:
        conn = _connect(self._db_path)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()

    async def get_connection_pool(self) -> str:
        """SQLite needs no pool; return the path as a handle.

        The abstract base declares this method; higher-level code in this
        project only calls ``execute_query``/``extract_metadata`` on the
        adapter, so we simply return the database path.
        """
        return self._db_path

    async def close_connection_pool(self) -> None:
        """No persistent connections to close for SQLite."""
        self._pool = None

    # -- metadata ---------------------------------------------------------

    async def extract_metadata(self) -> MetadataResult:
        """Extract tables, views and column metadata from sqlite_master."""
        return await asyncio.get_event_loop().run_in_executor(
            _EXECUTOR, self._extract_metadata_sync
        )

    def _extract_metadata_sync(self) -> MetadataResult:
        conn = _connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
                "ORDER BY type, name"
            ).fetchall()

            tables: List[Dict[str, Any]] = []
            views: List[Dict[str, Any]] = []
            for row in rows:
                name = row["name"]
                table_type = row["type"]
                columns = self._get_columns_sync(conn, name)
                row_count: Optional[int] = None
                if table_type == "table":
                    try:
                        row_count = conn.execute(
                            f'SELECT COUNT(*) FROM "{name}"'
                        ).fetchone()[0]
                    except Exception:
                        row_count = None
                meta = {
                    "name": name,
                    "type": table_type,
                    "schemaName": "main",
                    "columns": columns,
                }
                if row_count is not None:
                    meta["rowCount"] = row_count
                if table_type == "table":
                    tables.append(meta)
                else:
                    views.append(meta)
            return MetadataResult(tables=tables, views=views)
        finally:
            conn.close()

    def _get_columns_sync(
        self, conn: sqlite3.Connection, table_name: str
    ) -> List[Dict[str, Any]]:
        """Return column metadata for a table using PRAGMA table_info."""
        pk_cols = {
            r["name"]
            for r in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            if r["pk"] > 0
        }
        foreign_cols = self._foreign_key_columns(conn, table_name)

        columns: List[Dict[str, Any]] = []
        for r in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall():
            col_name = r["name"]
            columns.append(
                {
                    "name": col_name,
                    "dataType": (r["type"] or "TEXT").lower(),
                    "nullable": r["notnull"] == 0,
                    "primaryKey": r["pk"] > 0,
                    "unique": col_name in pk_cols or col_name in foreign_cols.get("unique", set()),
                    "defaultValue": r["dflt_value"],
                }
            )
        return columns

    @staticmethod
    def _foreign_key_columns(
        conn: sqlite3.Connection, table_name: str
    ) -> Dict[str, set]:
        """Collect unique-index columns (best-effort, used for metadata flags)."""
        unique: set = set()
        try:
            for idx in conn.execute(
                f'PRAGMA index_list("{table_name}")'
            ).fetchall():
                if idx["unique"]:
                    for ic in conn.execute(
                        f'PRAGMA index_info("{idx["name"]}")'
                    ).fetchall():
                        unique.add(ic["name"])
        except Exception:
            pass
        return {"unique": unique}

    # -- query execution --------------------------------------------------

    async def execute_query(self, sql: str) -> QueryResult:
        """Run a SELECT statement and return rows as dict records."""
        return await asyncio.get_event_loop().run_in_executor(
            _EXECUTOR, self._execute_query_sync, sql
        )

    def _execute_query_sync(self, sql: str) -> QueryResult:
        conn = _connect(self._db_path)
        try:
            cursor = conn.execute(sql)
            raw_rows = cursor.fetchall()

            columns: List[Dict[str, str]] = []
            result_rows: List[Dict[str, Any]] = []

            if raw_rows:
                col_names = raw_rows[0].keys()
                for key in col_names:
                    columns.append(
                        {"name": key, "dataType": _infer_type(raw_rows[0][key])}
                    )
                for row in raw_rows:
                    result_rows.append(dict(row))

            return QueryResult(
                columns=columns,
                rows=result_rows,
                row_count=len(result_rows),
            )
        finally:
            conn.close()

    # -- dialect metadata -------------------------------------------------

    def get_dialect_name(self) -> str:
        """sqlglot dialect name for SQLite."""
        return "sqlite"

    def get_identifier_quote_char(self) -> str:
        """SQLite uses double quotes for identifiers."""
        return '"'
