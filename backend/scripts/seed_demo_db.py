#!/usr/bin/env python3
"""Create and seed a demo SQLite database.

This script builds a zero-install demo database so the full-stack tool (and
the new export feature) can be tried without PostgreSQL/MySQL. It creates a
file at ``backend/demo.db`` with several tables and realistic sample data,
including Chinese text, which is useful for demonstrating that CSV export is
UTF-8 BOM encoded (opens cleanly in Excel).

Usage:
    python scripts/seed_demo_db.py
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Resolve backend/demo.db regardless of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "demo.db"


SCHEMA = """
DROP TABLE IF EXISTS salaries;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL UNIQUE,
    budget REAL NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE employees (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    role          TEXT NOT NULL,
    hire_date     TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE salaries (
    id          INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    amount      REAL NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'CNY',
    effective_date TEXT NOT NULL
);
"""


DEPARTMENTS = [
    (1, "研发部", 5000000.0, "北京"),
    (2, "产品部", 2500000.0, "上海"),
    (3, "市场部", 1800000.0, "广州"),
    (4, "人事部", 900000.0, "深圳"),
    (5, "财务部", 1200000.0, "杭州"),
]

EMPLOYEES = [
    (1, "张伟", "zhangwei@example.com", 1, "高级工程师", "2021-03-15", 1),
    (2, "王芳", "wangfang@example.com", 1, "前端工程师", "2022-07-01", 1),
    (3, "李娜", "lina@example.com", 2, "产品经理", "2020-11-20", 1),
    (4, "刘强", "liuqiang@example.com", 1, "架构师", "2019-05-10", 1),
    (5, "陈静", "chenjing@example.com", 3, "市场专员", "2023-02-14", 1),
    (6, "杨洋", "yangyang@example.com", 2, "UX 设计师", "2022-09-05", 1),
    (7, "赵磊", "zhaolei@example.com", 4, "HRBP", "2021-12-01", 0),
    (8, "黄敏", "huangmin@example.com", 5, "会计", "2020-06-18", 1),
    (9, "周杰", "zhoujie@example.com", 1, "后端工程师", "2023-08-22", 1),
    (10, "吴婷", "wuting@example.com", 3, "市场总监", "2018-04-03", 1),
]

SALARIES = [
    (1, 1, 35000.0, "CNY", "2024-01-01"),
    (2, 2, 22000.0, "CNY", "2024-01-01"),
    (3, 3, 30000.0, "CNY", "2024-01-01"),
    (4, 4, 48000.0, "CNY", "2024-01-01"),
    (5, 5, 15000.0, "CNY", "2024-01-01"),
    (6, 6, 24000.0, "CNY", "2024-01-01"),
    (7, 7, 18000.0, "CNY", "2024-01-01"),
    (8, 8, 20000.0, "CNY", "2024-01-01"),
    (9, 9, 21000.0, "CNY", "2024-01-01"),
    (10, 10, 40000.0, "CNY", "2024-01-01"),
    (11, 1, 38000.0, "CNY", "2025-01-01"),
    (12, 4, 52000.0, "CNY", "2025-01-01"),
    (13, 9, 25000.0, "CNY", "2025-01-01"),
]


def seed() -> Path:
    """(Re)create the demo database and return its path."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO departments(id, name, budget, location) VALUES (?, ?, ?, ?)",
            DEPARTMENTS,
        )
        conn.executemany(
            "INSERT INTO employees(id, name, email, department_id, role, hire_date, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            EMPLOYEES,
        )
        conn.executemany(
            "INSERT INTO salaries(id, employee_id, amount, currency, effective_date) "
            "VALUES (?, ?, ?, ?, ?)",
            SALARIES,
        )
        conn.commit()
    finally:
        conn.close()

    return DB_PATH


def main() -> None:
    path = seed()
    print(f"[seed] Demo database created at: {path}")
    print(f"[seed]   departments : {len(DEPARTMENTS)} rows")
    print(f"[seed]   employees   : {len(EMPLOYEES)} rows")
    print(f"[seed]   salaries    : {len(SALARIES)} rows")
    print("[seed] Connection URL for the UI:")
    print(f"[seed]   sqlite:///{path.as_posix()}")


if __name__ == "__main__":
    main()
