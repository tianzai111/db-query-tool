#!/usr/bin/env python3
"""One-click query + export CLI (Agent automation demo).

This script demonstrates the "automation workflow" part of the assignment:
using a single command to complete both "execute query" and "export results".
It talks to the running backend's ``/api/v1/dbs/{name}/export`` endpoint, so
the same task decomposition (validate -> run -> format -> save -> report)
lives on the server and can be driven from a terminal, curl, or any AI agent.

Example
-------
    python scripts/export_query.py mydb "SELECT id, name FROM users LIMIT 10" --format csv

If you have a direct PostgreSQL/MySQL URL instead of a registered connection,
this script can also run fully standalone using the in-process
``app.services.export`` module (see ``--standalone``).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.error
import urllib.request
import json
from pathlib import Path


def http_export(base_url: str, db_name: str, sql: str, fmt: str, out: Path) -> None:
    """Call the backend /export endpoint and stream the file to disk."""
    url = f"{base_url.rstrip('/')}/api/v1/dbs/{db_name}/export"
    payload = json.dumps({"sql": sql, "format": fmt}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            # Prefer the server-suggested filename.
            disposition = resp.headers.get("Content-Disposition", "")
            filename = out.name
            if 'filename="' in disposition:
                filename = disposition.split('filename="')[1].split('"')[0]
            target = out if out.is_file() or out.suffix else out / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print(f"[export] Saved {len(data):,} bytes -> {target}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[export] HTTP {e.code}: {body}", file=sys.stderr)
        raise SystemExit(1) from e


async def standalone_export(url: str, sql: str, fmt: str, out: Path) -> None:
    """Run the export fully in-process (no backend server required)."""
    # Heavy imports are kept here so the HTTP mode works with the stdlib only.
    from app.services import connection_factory
    from app.models.database import DatabaseType
    from app.services.sql_validator import validate_and_transform_sql
    from app.models.schemas import QueryColumn
    from app.services.export import ExportFormat, export_result

    db_type = DatabaseType.POSTGRESQL if url.startswith("postgresql") else DatabaseType.MYSQL
    validated = validate_and_transform_sql(sql, limit=1000, db_type=db_type)
    pool = await connection_factory.get_connection_pool(db_type, "cli", url)
    start = __import__("time").time()
    if db_type == DatabaseType.POSTGRESQL:
        async with pool.acquire() as conn:
            rows = await conn.fetch(validated)
        columns = []
        result_rows = []
        if rows:
            for key in rows[0].keys():
                columns.append(QueryColumn(name=key, dataType="unknown"))
            result_rows = [dict(r) for r in rows]
    else:
        from app.services import mysql_query
        raw = await mysql_query.execute_query(pool, validated)
        columns = [QueryColumn(**c) for c in raw["columns"]]
        result_rows = raw["rows"]
    elapsed = int((__import__("time").time() - start) * 1000)

    from app.models.schemas import QueryResult
    result = QueryResult(
        columns=columns,
        rows=result_rows,
        rowCount=len(result_rows),
        executionTimeMs=elapsed,
        sql=validated,
    )
    content, filename = export_result(result, ExportFormat(fmt), database_name="standalone")
    target = out / filename if out.is_dir() or not out.suffix else out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    print(f"[export] Saved {len(content):,} bytes -> {target}")
    # Cleanup pools.
    from app.services.db_connection import close_all_connection_pools
    await close_all_connection_pools()


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click query + export tool")
    parser.add_argument("database", help="Registered database name (or DB URL with --standalone)")
    parser.add_argument("sql", help="SELECT query to execute and export")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--out", type=Path, default=Path("."), help="Output file or directory")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument(
        "--standalone", action="store_true", help="Run in-process without a backend server"
    )
    args = parser.parse_args()

    if args.standalone:
        asyncio.run(standalone_export(args.database, args.sql, args.format, args.out))
    else:
        http_export(args.base_url, args.database, args.sql, args.format, args.out)


if __name__ == "__main__":
    main()
