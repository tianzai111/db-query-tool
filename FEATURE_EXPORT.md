# FEATURE_EXPORT.md — 数据导出功能设计文档

## 一、功能概述

在原有"智能数据库查询工具"基础上，新增 **数据导出功能模块**，支持将 SQL 查询结果导出为 **CSV** 和 **JSON** 两种格式，并通过 AI Agent 自动化流程实现"查询 + 导出"一键完成。

### 核心目标

| 目标 | 说明 |
|------|------|
| 导出格式支持 | CSV（兼容 Excel 打开，UTF-8 BOM 编码）、JSON（含元数据结构） |
| 自动化流程 | 通过 Agent 子任务编排，一条命令完成"查询 → 验证 → 格式化 → 导出" |
| 用户交互 | 查询后主动提示导出选项，支持自然语言式命令输入 |

---

## 二、设计思路

### 2.1 架构分层

```
┌─────────────────────────────────────────────────────┐
│                  用户交互层 (main.py)                │
│     交互式 CLI / 演示模式 / 自然语言入口               │
├─────────────────────────────────────────────────────┤
│              自定义命令层 (commands.py)               │
│   /query  /export  /run  /tables  /schema  /help    │
├─────────────────────────────────────────────────────┤
│              AI Agent 层 (agent.py)                  │
│   任务分解 → 子任务编排 → 结果传递 → 日志记录          │
├──────────────────┬──────────────────────────────────┤
│  数据库层          │    导出层 (exporter.py)           │
│  (database.py)   │    CSV / JSON 格式化与文件写入     │
│  连接·查询·结果    │                                  │
└──────────────────┴──────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 数据库管理 | `database.py` | 数据库连接、SQL 执行、查询结果封装（QueryResult） |
| 数据导出 | `exporter.py` | CSV/JSON 格式化、文件创建、摘要生成 |
| AI Agent | `agent.py` | 任务分解、子任务编排、工作流日志、错误处理 |
| 命令系统 | `commands.py` | 自定义命令注册与调度、自动化命令 `/run` |
| 主程序 | `main.py` | 交互式 CLI、演示模式、自然语言入口 |
| 数据初始化 | `setup_db.py` | 示例数据库创建（users/products/orders 三表） |

---

## 三、功能实现详解

### 3.1 导出格式支持

#### CSV 导出
- 使用 Python 标准库 `csv` 模块
- 编码：UTF-8 with BOM（`utf-8-sig`），确保 Excel 正确显示中文
- 结构：第一行为列名，后续为数据行

```python
with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(result.columns)
    writer.writerows(result.rows)
```

#### JSON 导出
- 使用 Python 标准库 `json` 模块
- 包含 `metadata`（导出时间、行数、执行耗时、SQL、列名）和 `data`（字典列表）两部分
- `ensure_ascii=False` 保留中文原文

```json
{
  "metadata": {
    "export_time": "2026-07-29T14:30:00",
    "row_count": 20,
    "execution_time_sec": 0.0012,
    "sql": "SELECT * FROM users",
    "columns": ["id", "name", "email", "department", "salary"]
  },
  "data": [
    {"id": 1, "name": "张伟", "email": "user01@example.com", ...},
    ...
  ]
}
```

### 3.2 自动化流程设计（AI Agent）

#### 任务分解

"导出数据"被分解为 5 个子任务，Agent 按顺序编排执行：

```
[1.获取查询结果] → [2.验证数据] → [3.格式化数据] → [4.创建文件] → [5.生成摘要]
```

| 子任务 | 输入 | 输出 | 失败处理 |
|--------|------|------|----------|
| 1. 获取查询结果 | SQL 语句 | QueryResult 对象 | 返回错误，中止流程 |
| 2. 验证数据 | QueryResult | bool（通过/不通过） | 空结果或无列信息则中止 |
| 3. 格式化数据 | QueryResult + 格式 | 格式化后的数据 | 异常则中止 |
| 4. 创建文件 | 格式化数据 + 路径 | 文件路径 | 写入失败则中止 |
| 5. 生成摘要 | QueryResult + 文件路径 | 摘要字符串 | 非关键步骤 |

#### Agent 工作流日志

Agent 在每个子任务执行时记录日志，可视化展示执行过程：

```
  1. [OK] fetch_query_result: 查询成功，返回 20 行，耗时 0.0012s
  2. [OK] validate_data: 验证通过: 6 列, 20 行
  3. [OK] format_data: 数据格式化完成
  4. [OK] create_file: 文件已创建: exports/query_result_20260729.csv
  5. [OK] generate_summary: 摘要生成完成
  6. [OK] workflow_complete: 导出完成: exports/query_result_20260729.csv
```

#### 核心代码

```python
class ExportAgent:
    def run_export_workflow(self, sql, format_type="csv", filename=None):
        # 子任务 1: 获取查询结果
        result = self._task_fetch_query_result(sql)
        if result is None:
            return {"success": False, ...}

        # 子任务 2: 验证数据
        if not self._task_validate_data(result):
            return {"success": False, ...}

        # 子任务 3 & 4: 格式化 + 创建文件
        filepath = self._task_format_and_create_file(result, format_type, filename)

        # 子任务 5: 生成摘要
        summary = self._task_generate_summary(result, filepath)

        return {"success": True, "filepath": filepath, ...}
```

### 3.3 自定义命令系统

模拟 Claude Code 的自定义 Command 功能，注册了以下命令：

| 命令 | 功能 | 对应作业要求 |
|------|------|-------------|
| `/tables` | 查看所有表 | 代码库理解 |
| `/schema <table>` | 查看表结构 | 代码库理解 |
| `/query <sql>` | 执行查询 | 基础功能 |
| `/export <format>` | 导出上次结果 | 导出功能 |
| `/run <sql> [format]` | 一键查询+导出 | **自动化流程** |
| `/help` | 帮助 | 用户交互 |
| `/exit` | 退出 | — |

`/run` 是自动化核心命令，它调用 Agent 的 `run_export_workflow` 方法，一条命令完成从查询到导出的全部步骤。

### 3.4 用户交互设计

#### 交互模式 1：分步操作
```
用户: /query SELECT * FROM users LIMIT 5
系统: 查询成功! 返回 5 行...
      > 需要将这次查询结果导出为 CSV 或 JSON 文件吗？
      输入 /export csv 或 /export json 或 /export all 进行导出

用户: /export json
系统: 导出完成! 文件: exports/query_result_20260729.json
```

#### 交互模式 2：一键自动化
```
用户: /run SELECT * FROM users LIMIT 5 json
系统: [Agent] 启动自动化工作流...
      1. [OK] fetch_query_result: ...
      2. [OK] validate_data: ...
      3. [OK] format_data: ...
      4. [OK] create_file: ...
      5. [OK] generate_summary: ...
      导出完成!
```

#### 交互模式 3：直接 SQL
```
用户: SELECT name, salary FROM users WHERE salary > 10000
系统: 查询成功! ...
      > 需要将这次查询结果导出为 CSV 或 JSON 文件吗？
```

---

## 四、工具链整合思考

### Cursor 与 Claude Code 的协同

| 工具 | 优势 | 在本项目中的应用 |
|------|------|-----------------|
| Cursor | 快速代码生成、实时补全、文件级编辑 | 快速编写 `database.py`、`exporter.py` 等模块代码；实时调试 SQL 查询逻辑 |
| Claude Code | 多步骤自动化、Agent 任务编排、自定义命令 | 实现 `/run` 自动化命令；Agent 将导出任务分解为子任务链；工作流日志可视化 |

### 结合方式
1. **开发阶段**：使用 Cursor 快速生成和迭代各模块代码，利用 AI 补全提高效率
2. **集成阶段**：使用 Claude Code 设计 Agent 工作流，将分散功能编排为自动化流程
3. **验证阶段**：通过 `/run` 命令一键验证"查询 + 导出"全链路

---

## 五、使用方法

### 快速开始

```bash
# 初始化示例数据库
python setup_db.py

# 交互模式
python main.py

# 演示模式（自动展示所有功能）
python main.py --demo
```

### 导出示例

```bash
# 交互模式中
db> /query SELECT * FROM users LIMIT 10
db> /export csv

# 一键模式
db> /run SELECT * FROM users LIMIT 10 csv
db> /run SELECT department, AVG(salary) as avg FROM users GROUP BY department json
```

### 导出文件位置

所有导出文件保存在 `exports/` 目录下：
```
exports/
├── query_result_20260729_143000.csv
├── query_result_20260729_143000.json
└── ...
```

---

## 六、扩展性设计

当前架构支持以下扩展方向：

1. **新增导出格式**：在 `exporter.py` 的 `SUPPORTED_FORMATS` 中添加格式，实现对应的 `_export_xxx` 方法
2. **新增 Agent 子任务**：在 `agent.py` 中添加子任务方法，并在 `run_export_workflow` 中编排
3. **新增自定义命令**：在 `commands.py` 的 `_register_commands` 中注册新命令
4. **支持多数据库**：`database.py` 抽象为接口，可扩展支持 MySQL/PostgreSQL
5. **集成真实 AI**：将自然语言转 SQL 的能力接入 Agent，实现"说人话 → 查数据 → 导出文件"
