"""
数据导出模块
支持将查询结果导出为 CSV 和 JSON 格式
"""

import csv
import json
import os
from datetime import datetime
from typing import Any

from database import QueryResult


class DataExporter:
    """数据导出器：支持 CSV / JSON 格式导出"""

    SUPPORTED_FORMATS = ["csv", "json"]

    def __init__(self, output_dir: str = "exports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export(
        self,
        result: QueryResult,
        format_type: str = "csv",
        filename: str | None = None,
    ) -> str:
        """
        导出查询结果到文件

        Args:
            result: 查询结果对象
            format_type: 导出格式 (csv / json)
            filename: 自定义文件名（不含扩展名）

        Returns:
            导出文件的完整路径
        """
        format_type = format_type.lower().strip()

        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的导出格式: {format_type}，支持: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        if result.is_empty():
            raise ValueError("查询结果为空，无法导出。")

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"query_result_{timestamp}"

        filepath = os.path.join(self.output_dir, f"{filename}.{format_type}")

        if format_type == "csv":
            self._export_csv(result, filepath)
        elif format_type == "json":
            self._export_json(result, filepath)

        return filepath

    def export_all(self, result: QueryResult, filename: str | None = None) -> dict[str, str]:
        """
        同时导出所有支持格式

        Returns:
            {格式: 文件路径} 的映射
        """
        results = {}
        for fmt in self.SUPPORTED_FORMATS:
            results[fmt] = self.export(result, fmt, filename)
        return results

    def _export_csv(self, result: QueryResult, filepath: str):
        """导出为 CSV 文件"""
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(result.columns)
            writer.writerows(result.rows)

    def _export_json(self, result: QueryResult, filepath: str):
        """导出为 JSON 文件"""
        data: dict[str, Any] = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "row_count": result.row_count,
                "execution_time_sec": round(result.execution_time, 4),
                "sql": result.sql,
                "columns": result.columns,
            },
            "data": result.to_dict_list(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_export_summary(self, filepath: str) -> str:
        """获取导出文件摘要信息"""
        size = os.path.getsize(filepath)
        size_str = f"{size} bytes"
        if size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"

        return f"文件: {os.path.basename(filepath)} | 大小: {size_str} | 路径: {os.path.abspath(filepath)}"
