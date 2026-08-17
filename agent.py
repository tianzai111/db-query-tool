"""
AI Agent 模块 - 任务分解与自动化流程编排
模拟 Claude Code Agent 的工作方式：将复杂任务分解为子任务并协调执行

设计思路：
  "导出数据" 被分解为以下子任务链：
  1. 获取查询结果  →  2. 验证数据  →  3. 格式化数据  →  4. 创建文件  →  5. 返回摘要

每个子任务是独立的、可测试的步骤，Agent 负责编排和传递中间结果。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

from database import DatabaseManager, QueryResult
from exporter import DataExporter


class TaskStatus(Enum):
    """子任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SubTask:
    """子任务定义"""
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""


@dataclass
class AgentLog:
    """Agent 执行日志"""
    steps: list[dict] = field(default_factory=list)

    def log(self, task_name: str, status: str, message: str = "", result: Any = None):
        self.steps.append({
            "task": task_name,
            "status": status,
            "message": message,
            "result": str(result)[:200] if result else "",
        })

    def __str__(self):
        lines = []
        for i, step in enumerate(self.steps, 1):
            icon = {"success": "[OK]", "failed": "[FAIL]", "running": "[...]", "pending": "[ ]"}.get(
                step["status"], "[?]"
            )
            lines.append(f"  {i}. {icon} {step['task']}: {step['message']}")
        return "\n".join(lines)


class ExportAgent:
    """
    数据导出 Agent
    将"导出数据"任务分解为子任务链并协调执行

    子任务分解：
      1. fetch_query_result  - 获取查询结果
      2. validate_data       - 验证数据完整性
      3. format_data         - 格式化数据为指定格式
      4. create_file         - 创建并写入文件
      5. generate_summary    - 生成导出摘要
    """

    def __init__(self, db_manager: DatabaseManager, exporter: DataExporter):
        self.db = db_manager
        self.exporter = exporter
        self.log = AgentLog()

    def run_export_workflow(
        self,
        sql: str,
        format_type: str = "csv",
        filename: str | None = None,
    ) -> dict:
        """
        执行完整的"查询 + 导出"自动化工作流

        这是 Agent 的核心编排方法，按顺序执行所有子任务
        如果任一子任务失败，Agent 会中止流程并返回错误信息
        """
        self.log = AgentLog()
        context: dict[str, Any] = {
            "sql": sql,
            "format": format_type,
            "filename": filename,
        }

        # ---- 子任务 1: 获取查询结果 ----
        result = self._task_fetch_query_result(sql)
        if result is None:
            return {"success": False, "error": "查询执行失败", "log": str(self.log)}
        context["result"] = result

        # ---- 子任务 2: 验证数据 ----
        if not self._task_validate_data(result):
            return {"success": False, "error": "数据验证失败", "log": str(self.log)}

        # ---- 子任务 3 & 4: 格式化数据 + 创建文件 ----
        filepath = self._task_format_and_create_file(result, format_type, filename)
        if filepath is None:
            return {"success": False, "error": "文件创建失败", "log": str(self.log)}
        context["filepath"] = filepath

        # ---- 子任务 5: 生成摘要 ----
        summary = self._task_generate_summary(result, filepath)
        context["summary"] = summary

        self.log.log("workflow_complete", "success", f"导出完成: {filepath}")

        return {
            "success": True,
            "filepath": filepath,
            "summary": summary,
            "row_count": result.row_count,
            "log": str(self.log),
        }

    def _task_fetch_query_result(self, sql: str) -> QueryResult | None:
        """子任务 1: 获取查询结果"""
        self.log.log("fetch_query_result", "running", f"执行查询: {sql[:60]}...")
        try:
            result = self.db.execute_query(sql)
            self.log.log(
                "fetch_query_result", "success",
                f"查询成功，返回 {result.row_count} 行，耗时 {result.execution_time:.4f}s"
            )
            return result
        except Exception as e:
            self.log.log("fetch_query_result", "failed", f"查询失败: {e}")
            return None

    def _task_validate_data(self, result: QueryResult) -> bool:
        """子任务 2: 验证数据完整性"""
        self.log.log("validate_data", "running", "验证数据完整性...")

        if result.is_empty():
            self.log.log("validate_data", "failed", "查询结果为空")
            return False

        if not result.columns:
            self.log.log("validate_data", "failed", "查询结果无列信息")
            return False

        # 检查是否有 NULL 值过多的列
        for i, col in enumerate(result.columns):
            null_count = sum(1 for row in result.rows if row[i] is None)
            if null_count == result.row_count:
                self.log.log(
                    "validate_data", "success",
                    f"警告: 列 '{col}' 全部为 NULL"
                )

        self.log.log(
            "validate_data", "success",
            f"验证通过: {len(result.columns)} 列, {result.row_count} 行"
        )
        return True

    def _task_format_and_create_file(
        self, result: QueryResult, format_type: str, filename: str | None
    ) -> str | None:
        """子任务 3 & 4: 格式化数据并创建文件"""
        self.log.log("format_data", "running", f"格式化为 {format_type.upper()} ...")

        try:
            filepath = self.exporter.export(result, format_type, filename)
            self.log.log("format_data", "success", f"数据格式化完成")
            self.log.log("create_file", "success", f"文件已创建: {filepath}")
            return filepath
        except Exception as e:
            self.log.log("create_file", "failed", f"文件创建失败: {e}")
            return None

    def _task_generate_summary(self, result: QueryResult, filepath: str) -> str:
        """子任务 5: 生成导出摘要"""
        summary = self.exporter.get_export_summary(filepath)
        full_summary = (
            f"导出完成!\n"
            f"  {summary}\n"
            f"  行数: {result.row_count} | 列数: {len(result.columns)}\n"
            f"  查询耗时: {result.execution_time:.4f}s\n"
            f"  SQL: {result.sql[:80]}{'...' if len(result.sql) > 80 else ''}"
        )
        self.log.log("generate_summary", "success", "摘要生成完成")
        return full_summary

    def print_workflow(self):
        """打印 Agent 工作流可视化"""
        print("\n" + "=" * 60)
        print("  ExportAgent 工作流")
        print("=" * 60)
        print("  [查询SQL] → [获取结果] → [验证数据] → [格式化] → [创建文件] → [摘要]")
        print("=" * 60)
        print(self.log)
        print("=" * 60 + "\n")
