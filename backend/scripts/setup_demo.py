#!/usr/bin/env python3
"""Prepare the zero-install demo environment.

This script:
1. Seeds ``backend/demo.db`` with sample data.
2. Registers the demo database connection in the app's own SQLite metadata DB,
   so it appears immediately in the sidebar (no manual "Add Database" needed).
3. Triggers a metadata refresh so the schema tree is populated on first load.

Run it once before starting the backend (the ``start-demo.ps1`` script does
this automatically).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# A dummy OpenAI key keeps Settings importable; NL-to-SQL isn't needed for the
# basic query/export demo.
os.environ.setdefault("OPENAI_API_KEY", "demo-key-not-real")

from sqlmodel import Session, select  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.models.database import DatabaseConnection, DatabaseType  # noqa: E402
from app.services.metadata import fetch_metadata  # noqa: E402
from scripts.seed_demo_db import seed as seed_demo  # noqa: E402

DEMO_DB_NAME = "demo"


def register_demo_connection(demo_db_path: Path) -> DatabaseConnection:
    """Insert (or update) the demo connection in the app metadata DB."""
    url = f"sqlite:///{demo_db_path.as_posix()}"
    with Session(engine) as session:
        existing = session.exec(
            select(DatabaseConnection).where(DatabaseConnection.name == DEMO_DB_NAME)
        ).first()
        if existing:
            existing.url = url
            existing.db_type = DatabaseType.SQLITE
            existing.description = "演示数据库 (SQLite, 零安装)"
            session.add(existing)
            session.commit()
            session.refresh(existing)
            conn = existing
        else:
            conn = DatabaseConnection(
                name=DEMO_DB_NAME,
                url=url,
                db_type=DatabaseType.SQLITE,
                description="演示数据库 (SQLite, 零安装)",
            )
            session.add(conn)
            session.commit()
            session.refresh(conn)
        return conn


async def warm_metadata(demo_db_path: Path) -> None:
    """Pre-populate the metadata cache so the schema tree shows on load."""
    from app.services.metadata import get_cached_metadata

    with Session(engine) as session:
        existing = await get_cached_metadata(session, DEMO_DB_NAME)
        if existing:
            print("[demo] Metadata already cached.")
            return
        url = f"sqlite:///{demo_db_path.as_posix()}"
        await fetch_metadata(session, DEMO_DB_NAME, DatabaseType.SQLITE, url)
        print("[demo] Metadata cached.")


def main() -> None:
    init_db()
    demo_db_path = seed_demo()
    conn = register_demo_connection(demo_db_path)
    print(f"[demo] Registered connection '{conn.name}' -> {conn.url}")
    asyncio.run(warm_metadata(demo_db_path))
    print("[demo] Ready. Start the backend and open the frontend.")


if __name__ == "__main__":
    main()
