# 智能数据库查询工具 v2.0

> 实战作业（一）：为"数据库查询工具"添加数据导出功能

## 功能特性

- SQL 查询执行（仅允许 SELECT，安全防护）
- 数据导出：CSV（UTF-8 BOM 兼容 Excel）和 JSON（含元数据）
- AI Agent 自动化：任务分解 → 子任务编排 → 一键导出
- 自定义命令系统：`/query`、`/export`、`/run` 等
- 交互式 CLI：查询后主动询问是否导出
- 示例数据库：users / products / orders 三表

## 快速开始

```bash
# 1. 初始化示例数据库
python setup_db.py

# 2. 运行演示（自动展示全部功能）
python main.py --demo

# 3. 交互模式
python main.py
```

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/tables` | 查看所有表 | `/tables` |
| `/schema <表名>` | 查看表结构 | `/schema users` |
| `/query <sql>` | 执行查询 | `/query SELECT * FROM users LIMIT 5` |
| `/export <格式>` | 导出上次结果 | `/export csv` / `/export json` / `/export all` |
| `/run <sql> [格式]` | 一键查询+导出 | `/run SELECT * FROM users LIMIT 10 csv` |
| `/help` | 帮助 | `/help` |
| `/exit` | 退出 | `/exit` |

也可以直接输入 SQL 语句，查询后系统会主动提示导出。

## 项目结构

```
db_query_tool/
├── main.py            # 主程序入口
├── database.py        # 数据库管理模块
├── exporter.py        # 数据导出模块 (CSV/JSON)
├── agent.py           # AI Agent 任务分解与自动化
├── commands.py        # 自定义命令系统
├── setup_db.py        # 示例数据库初始化
├── FEATURE_EXPORT.md  # 功能设计文档
├── README.md          # 项目说明
└── exports/           # 导出文件目录
```

## 依赖

- Python 3.10+
- 仅使用标准库，无需安装第三方包

## 技术要点

1. **代码库理解与扩展**：模块化设计，各层职责清晰，新增导出功能不影响原有查询逻辑
2. **AI Agent 任务分解**：将"导出数据"分解为 5 个子任务（获取结果→验证→格式化→创建文件→摘要）
3. **工具链整合**：Cursor 负责快速代码生成，Claude Code 负责多步骤自动化编排
