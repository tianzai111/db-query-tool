"""
自定义命令系统
模拟 Claude Code 自定义 Command 功能，提供一键式操作命令

可用命令：
  /tables          - 查看所有表
  /schema <table>  - 查看表结构
  /query <sql>     - 执行查询
  /export <format> - 导出上次查询结果 (csv/json/all)
  /run <sql>       - 一键查询+导出 (自动化命令)
  /help            - 查看帮助
  /exit            - 退出
"""

from database import DatabaseManager
from exporter import DataExporter
from agent import ExportAgent


class CommandRegistry:
    """命令注册表：管理和调度自定义命令"""

    def __init__(self, db: DatabaseManager, exporter: DataExporter, agent: ExportAgent):
        self.db = db
        self.exporter = exporter
        self.agent = agent
        self._commands: dict[str, dict] = {}
        self._register_commands()

    def _register_commands(self):
        """注册所有自定义命令"""
        self._commands = {
            "/tables": {
                "description": "查看数据库中所有表",
                "usage": "/tables",
                "handler": self._cmd_tables,
            },
            "/schema": {
                "description": "查看指定表的结构",
                "usage": "/schema <表名>",
                "handler": self._cmd_schema,
            },
            "/query": {
                "description": "执行 SQL 查询",
                "usage": "/query <SQL语句>",
                "handler": self._cmd_query,
            },
            "/export": {
                "description": "导出最近一次查询结果",
                "usage": "/export <csv|json|all>",
                "handler": self._cmd_export,
            },
            "/run": {
                "description": "一键查询 + 导出（自动化命令）",
                "usage": "/run <SQL语句> [格式]",
                "handler": self._cmd_run,
            },
            "/help": {
                "description": "查看所有可用命令",
                "usage": "/help",
                "handler": self._cmd_help,
            },
            "/exit": {
                "description": "退出程序",
                "usage": "/exit",
                "handler": self._cmd_exit,
            },
        }

    def execute(self, user_input: str) -> bool:
        """
        解析并执行命令

        Returns:
            False 表示需要退出程序，True 表示继续
        """
        parts = user_input.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd not in self._commands:
            print(f"  未知命令: {cmd}，输入 /help 查看可用命令")
            return True

        handler = self._commands[cmd]["handler"]
        return handler(args)

    # ===== 命令处理器 =====

    def _cmd_tables(self, args: str) -> bool:
        """命令: /tables - 查看所有表"""
        tables = self.db.get_tables()
        if not tables:
            print("  数据库中没有表。请先运行 setup_db.py 初始化示例数据。")
            return True

        print("\n  数据库表列表:")
        print("  " + "-" * 40)
        for i, table in enumerate(tables, 1):
            print(f"  {i}. {table}")
        print("  " + "-" * 40)
        return True

    def _cmd_schema(self, args: str) -> bool:
        """命令: /schema <table> - 查看表结构"""
        if not args:
            print("  用法: /schema <表名>")
            return True

        table_name = args.strip()
        schema = self.db.get_table_schema(table_name)

        if not schema:
            print(f"  表 '{table_name}' 不存在或无结构信息")
            return True

        print(f"\n  表 '{table_name}' 结构:")
        print("  " + "-" * 50)
        print(f"  {'列名':<20} {'类型':<15} {'非空':<6} {'主键'}")
        print("  " + "-" * 50)
        for col in schema:
            pk = "是" if col["pk"] else ""
            notnull = "是" if col["notnull"] else "否"
            print(f"  {col['name']:<20} {col['type']:<15} {notnull:<6} {pk}")
        print("  " + "-" * 50)
        return True

    def _cmd_query(self, args: str) -> bool:
        """命令: /query <sql> - 执行查询"""
        if not args:
            print("  用法: /query <SQL语句>")
            print("  示例: /query SELECT * FROM users LIMIT 5")
            return True

        try:
            result = self.db.execute_query(args)
            print(f"\n  查询成功! 返回 {result.row_count} 行, 耗时 {result.execution_time:.4f}s\n")
            print(result.preview(10))

            # 主动询问是否导出
            if not result.is_empty():
                print("\n  > 需要将这次查询结果导出为 CSV 或 JSON 文件吗？")
                print("    输入 /export csv 或 /export json 或 /export all 进行导出")
        except ValueError as e:
            print(f"  [错误] {e}")
        except Exception as e:
            print(f"  [错误] 查询失败: {e}")
        return True

    def _cmd_export(self, args: str) -> bool:
        """命令: /export <format> - 导出上次查询结果"""
        if not args:
            print("  用法: /export <csv|json|all>")
            return True

        result = self.db.last_result
        if result is None or result.is_empty():
            print("  没有可导出的查询结果，请先执行查询 (/query)")
            return True

        format_type = args.strip().lower()

        try:
            if format_type == "all":
                paths = self.exporter.export_all(result)
                print("\n  导出完成! 所有格式:")
                for fmt, path in paths.items():
                    summary = self.exporter.get_export_summary(path)
                    print(f"    [{fmt.upper()}] {summary}")
            else:
                filepath = self.exporter.export(result, format_type)
                summary = self.exporter.get_export_summary(filepath)
                print(f"\n  导出完成!")
                print(f"    {summary}")
        except Exception as e:
            print(f"  [错误] 导出失败: {e}")
        return True

    def _cmd_run(self, args: str) -> bool:
        """
        命令: /run <sql> [format] - 一键查询+导出
        这是自动化核心命令，调用 Agent 工作流
        """
        if not args:
            print("  用法: /run <SQL语句> [导出格式]")
            print("  示例: /run SELECT * FROM users LIMIT 10 csv")
            print("        /run SELECT * FROM products WHERE price > 100 json")
            return True

        parts = args.rsplit(maxsplit=1)
        sql = parts[0]
        format_type = parts[1] if len(parts) > 1 else "csv"

        # 调用 Agent 执行自动化工作流
        print(f"\n  [Agent] 启动自动化工作流: 查询 + 导出({format_type})")
        print(f"  [Agent] SQL: {sql}")
        print()

        result = self.agent.run_export_workflow(sql, format_type)

        self.agent.print_workflow()

        if result["success"]:
            print(f"  {result['summary']}")
            print(f"\n  文件路径: {result['filepath']}")
        else:
            print(f"  [错误] {result['error']}")
        return True

    def _cmd_help(self, args: str) -> bool:
        """命令: /help - 查看帮助"""
        print("\n  可用命令:")
        print("  " + "=" * 55)
        for cmd, info in self._commands.items():
            print(f"  {cmd:<12} {info['description']}")
            print(f"  {'':12} 用法: {info['usage']}")
        print("  " + "=" * 55)
        print("\n  也可以直接输入 SQL 语句进行查询")
        print("  查询后系统会主动询问是否需要导出\n")
        return True

    def _cmd_exit(self, args: str) -> bool:
        """命令: /exit - 退出"""
        print("  再见!")
        return False
