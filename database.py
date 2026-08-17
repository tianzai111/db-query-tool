"""
数据库查询核心模块
负责数据库连接、SQL执行、结果管理
"""

import sqlite3
from typing import Any
from dataclasses import dataclass, field


@dataclass
class QueryResult:
    """查询结果数据结构"""
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    row_count: int = 0
    execution_time: float = 0.0
    sql: str = ""

    def to_dict_list(self) -> list[dict[str, Any]]:
        """将查询结果转换为字典列表，方便导出"""
        return [dict(zip(self.columns, row)) for row in self.rows]

    def is_empty(self) -> bool:
        return self.row_count == 0

    def preview(self, n: int = 5) -> str:
        """生成结果预览字符串"""
        if self.is_empty():
            return "（无查询结果）"

        lines = []
        header = " | ".join(self.columns)
        separator = "-+-".join(["-" * len(col) for col in self.columns])
        lines.append(header)
        lines.append(separator)

        for row in self.rows[:n]:
            lines.append(" | ".join(str(val) for val in row))

        if self.row_count > n:
            lines.append(f"... 共 {self.row_count} 行，仅显示前 {n} 行")

        return "\n".join(lines)


class DatabaseManager:
    """数据库管理器：连接、查询、结果管理"""

    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None
        self._last_result: QueryResult | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def connect(self) -> bool:
        """连接数据库"""
        try:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"[错误] 数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute_query(self, sql: str) -> QueryResult:
        """执行SQL查询并返回结果"""
        import time

        sql = sql.strip().rstrip(";")

        # 安全检查：只允许 SELECT 查询
        if not sql.upper().startswith("SELECT") and not sql.upper().startswith("WITH"):
            raise ValueError("仅允许执行 SELECT 查询语句。删除/更新操作请使用专用工具。")

        start_time = time.time()
        cursor = self.connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        execution_time = time.time() - start_time

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        row_tuples = [tuple(row) for row in rows]

        result = QueryResult(
            columns=columns,
            rows=row_tuples,
            row_count=len(row_tuples),
            execution_time=execution_time,
            sql=sql,
        )

        self._last_result = result
        return result

    def get_tables(self) -> list[str]:
        """获取数据库中所有表名"""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_table_schema(self, table_name: str) -> list[dict[str, str]]:
        """获取表结构信息"""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [
            {"name": row[1], "type": row[2], "notnull": row[3], "pk": row[5]}
            for row in cursor.fetchall()
        ]

    @property
    def last_result(self) -> QueryResult | None:
        """获取最近一次查询结果"""
        return self._last_result
