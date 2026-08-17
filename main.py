"""
智能数据库查询工具 - 主程序
交互式 CLI 界面，支持自然语言和命令式操作

使用方式:
    python main.py              # 交互模式
    python main.py --demo       # 演示模式（自动执行示例操作）
"""

import sys
import os

from database import DatabaseManager
from exporter import DataExporter
from agent import ExportAgent
from commands import CommandRegistry

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")


def print_banner():
    """打印欢迎横幅"""
    print("""
  ╔══════════════════════════════════════════════════════╗
  ║          智能数据库查询工具 v2.0                     ║
  ║          支持查询 + 数据导出 (CSV / JSON)            ║
  ╚══════════════════════════════════════════════════════╝

  输入 /help 查看可用命令
  输入 SQL 语句直接查询 (如: SELECT * FROM users LIMIT 5)
  输入 /exit 退出
""")


def run_interactive(db: DatabaseManager, exporter: DataExporter, agent: ExportAgent):
    """运行交互式命令行"""
    registry = CommandRegistry(db, exporter, agent)

    print_banner()

    # 检查数据库是否有表
    tables = db.get_tables()
    if not tables:
        print("  [提示] 数据库为空，正在自动初始化示例数据...")
        from setup_db import init_database
        db.close()
        init_database(DB_PATH)
        db.connect()
        print("  [完成] 示例数据已初始化!\n")

    while True:
        try:
            user_input = input("  db> ").strip()

            if not user_input:
                continue

            # 以 / 开头的命令
            if user_input.startswith("/"):
                should_continue = registry.execute(user_input)
                if not should_continue:
                    break
            else:
                # 直接输入 SQL 语句
                try:
                    result = db.execute_query(user_input)
                    print(f"\n  查询成功! 返回 {result.row_count} 行, 耗时 {result.execution_time:.4f}s\n")
                    print(result.preview(10))

                    # 主动询问是否导出（用户交互设计）
                    if not result.is_empty():
                        print("\n  > 需要将这次查询结果导出为 CSV 或 JSON 文件吗？")
                        print("    输入 /export csv 或 /export json 或 /export all 进行导出")
                except ValueError as e:
                    print(f"  [错误] {e}")
                except Exception as e:
                    print(f"  [错误] 查询失败: {e}")

        except KeyboardInterrupt:
            print("\n  (输入 /exit 退出)")
        except EOFError:
            print("\n  再见!")
            break


def run_demo(db: DatabaseManager, exporter: DataExporter, agent: ExportAgent):
    """演示模式：自动执行完整功能展示"""
    registry = CommandRegistry(db, exporter, agent)

    print_banner()

    # 检查数据库
    tables = db.get_tables()
    if not tables:
        print("  [初始化] 正在创建示例数据库...")
        from setup_db import init_database
        db.close()
        init_database(DB_PATH)
        db.connect()
        print("  [完成] 示例数据已初始化!\n")

    demo_commands = [
        "/tables",
        "/schema users",
        "/query SELECT * FROM users LIMIT 5",
        "/export csv",
        "/export json",
        "/run SELECT name, department, salary FROM users WHERE salary > 8000 ORDER BY salary DESC json",
        "/run SELECT department, COUNT(*) as count, AVG(salary) as avg_salary FROM users GROUP BY department csv",
    ]

    for cmd in demo_commands:
        print(f"\n{'='*60}")
        print(f"  执行命令: {cmd}")
        print(f"{'='*60}")
        registry.execute(cmd)

    print(f"\n{'='*60}")
    print("  演示完成! 导出文件位于 exports/ 目录")
    print(f"{'='*60}\n")


def main():
    """程序入口"""
    db = DatabaseManager(DB_PATH)
    exporter = DataExporter(EXPORT_DIR)
    agent = ExportAgent(db, exporter)

    try:
        if "--demo" in sys.argv:
            run_demo(db, exporter, agent)
        else:
            run_interactive(db, exporter, agent)
    finally:
        db.close()


if __name__ == "__main__":
    main()
