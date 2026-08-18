# FEATURE_EXPORT — 数据导出功能模块设计文档

> 作业：在使用 Cursor 构建的"智能数据库查询工具"基础上，新增**数据导出功能模块**。
> 本文档说明新增功能的设计思路、任务分解、实现细节与验证方法。

## 1. 需求回顾

来自《实战作业（一）要求》：

1. **导出格式**：支持将查询结果导出为至少两种格式（CSV、JSON）。
2. **自动化工作流**：使用 Claude Code 的 Agent 或自定义 Command，设计自动化步骤，使"执行查询"和"导出结果"可一键完成或由简单命令触发。
3. **用户交互**：查询后，AI 助手主动询问"是否需要将本次查询结果导出为 CSV 或 JSON？"。
4. **核心练习点**：
   - 代码库理解与扩展；
   - AI Agent 任务分解（把"导出数据"拆成"获取结果 / 校验 / 格式化 / 生成文件 / 汇总"等子任务）；
   - 工具链配合（Cursor 生成代码，Claude Code 做多步骤自动化）。
5. **交付物**：更新后的项目代码 + 本设计文档 `FEATURE_EXPORT.md`。

## 2. 现有代码库分析

官方仓库 `w2/db_query` 是一个 FastAPI + React/TypeScript 的全栈项目：

```
backend/app/
├── api/v1/queries.py        # 查询相关 REST 接口
├── services/
│   ├── query.py             # 查询历史保存
│   ├── query_wrapper.py     # 执行查询并落历史
│   ├── database_service.py  # 通过 adapter 执行 SQL
│   ├── sql_validator.py     # 只读校验 + LIMIT 注入
│   └── connection_factory.py
├── adapters/                # PostgreSQL / MySQL 适配器
├── models/schemas.py        # Pydantic 请求/响应模型（camelCase）
└── main.py                  # FastAPI 入口

frontend/src/
├── pages/Home.tsx           # 主工作台（SQL 编辑器 + 结果表）
├── pages/queries/execute.tsx
├── components/ResultTable.tsx
├── services/api.ts          # axios 客户端
└── types/query.ts
```

关键事实：
- `POST /api/v1/dbs/{name}/query` 已返回 `QueryResult{columns, rows, rowCount, executionTimeMs, sql}`。
- 前端 `Home.tsx` 原本带有一段**内联**的 CSV/JSON 导出逻辑，但仅在浏览器端拼接字符串，没有后端导出接口，无法被脚本 / Agent 一键调用，也缺少主动提示与可复用组件。
- 后端已有完善的 SQL 只读校验（`validate_and_transform_sql`）与查询历史记录，导出功能应**复用**这些能力，而不是重新连接数据库。

## 3. 设计目标与原则

| 目标 | 设计决策 |
| --- | --- |
| 至少支持 CSV、JSON | 后端 `ExportFormat` 枚举 + 前端 `ExportFormat` 类型 |
| 一键"执行+导出" | 新增 `POST /api/v1/dbs/{name}/export`，单次请求完成 SQL 执行与文件下载 |
| 主动询问导出 | 新增前端 `ExportPrompt` 组件，查询成功且有数据时自动出现 |
| 可复用、可测试 | 把格式化逻辑抽到纯函数服务 `services/export.py`，与 HTTP 层解耦 |
| 中文/Excel 友好 | CSV 使用 **UTF-8 BOM** + CRLF（RFC 4180），Excel 直接双击不乱码 |
| JSON 自带上下文 | JSON 包含 `metadata`（列、SQL、行数、耗时、生成时间）与 `rows` |
| Agent 可调用 | 提供 Claude Code 自定义命令 `/export-query`、Cursor 规则、CLI 脚本 |
| 安全 | 导出同样走只读校验，禁止 INSERT/UPDATE/DELETE/DDL |

## 4. 架构与数据流

### 4.1 两种导出路径

1. **客户端导出（即时）**：结果已经在浏览器中，直接在前端把 `QueryResult` 序列化为 CSV/JSON 并下载，零额外请求。
2. **服务端导出（一键自动化）**：Agent / 脚本 / 工具栏调用后端 `/export`，后端执行 SQL（复用校验、连接池、历史记录），再以文件流返回。适合"无需先在界面查询，直接出文件"的自动化场景。

```
                       ┌──────────────────────────────┐
   UI / Agent / CLI ──►│ POST /dbs/{name}/export       │
                       │  { sql, format: csv|json }    │
                       └──────────────┬───────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │ execute_query_with_service()        │
                    │  (SQL 校验 / 连接池 / 写历史)        │
                    └─────────────────┬──────────────────┘
                                      │ QueryResult
                    ┌─────────────────▼──────────────────┐
                    │ services/export.py                 │
                    │  _to_csv() / _to_json()            │
                    │  build_filename()                  │
                    └─────────────────┬──────────────────┘
                                      │ bytes + filename
                                      ▼
                              Response(attachment)
```

### 4.2 AI Agent 任务分解

把"导出数据"拆成 5 个可独立验证的子任务（对应 `cursor/rules` 与 Claude 命令）：

1. **获取查询结果**：调用 `/query` 或 `/export`，复用已有服务。
2. **校验**：确认是只读 `SELECT`，确认结果非空。
3. **格式化**：CSV（BOM + 转义）或 JSON（metadata + rows）。
4. **生成文件**：返回 `Content-Disposition: attachment`，文件名 `<db>_query_<UTC时间戳>.<ext>`。
5. **汇总反馈**：输出文件名、大小、行数。

## 5. 后端实现

### 5.1 新增文件

**`backend/app/services/export.py`**（核心、纯函数、易测试）：
- `ExportFormat` 枚举：`csv` / `json`，提供 `from_string()`、`media_type`、`file_extension`。
- `_to_csv(result)`：使用 `csv.writer`，CRLF 换行，输出 UTF-8 BOM。
- `_to_json(result, database_name)`：结构化输出，`_json_safe()` 统一处理 `datetime`/`Decimal`/`UUID` 等不可直接序列化的类型。
- `build_filename(db, fmt, timestamp)`：生成确定性文件名，如 `mydb_query_20260422T103000Z.csv`。
- `export_result(result, fmt, database_name)` -> `(bytes, filename)` 对外统一入口。

### 5.2 修改文件

**`backend/app/models/schemas.py`** —— 新增请求模型：
```python
class ExportRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    format: Literal["csv", "json"] = "csv"
```

**`backend/app/api/v1/queries.py`** —— 新增接口：
```
POST /api/v1/dbs/{name}/export
Body: { "sql": "...", "format": "csv" }
Response: 文件流（Content-Type: text/csv 或 application/json；
          Content-Disposition: attachment; filename="..."）
```
错误处理：连接不存在返回 404，格式非法返回 400，SQL 校验失败返回 400，执行失败返回 500。该接口内部直接调用已有的 `execute_query_with_service()`，因此自动获得：SQL 只读校验、LIMIT 保护、PostgreSQL/MySQL 双适配、查询历史记录。

### 5.3 单元测试

**`backend/tests/unit/test_export.py`** 覆盖：
- 格式解析大小写不敏感、非法格式抛错；
- CSV 以 BOM 开头、表头正确、含逗号的值被引号包裹、`None` 输出为空；
- JSON 包含 `metadata`（database/rowCount/sql/columns）与 `rows`；
- 文件名生成确定性。

## 6. 前端实现

### 6.1 新增文件

| 文件 | 作用 |
| --- | --- |
| `frontend/src/services/export.ts` | 导出工具：`resultToCsv`/`resultToJson`、`exportResultClient`（浏览器端）、`exportResultServer`（调用后端 `/export`，支持进度回调、解析 `Content-Disposition` 文件名） |
| `frontend/src/components/ExportButtons.tsx` | 可复用 CSV/JSON 按钮组，支持普通双按钮与 `compact` 下拉两种形态 |
| `frontend/src/components/ExportPrompt.tsx` | AI 助手主动提示条："您的查询返回 N 行，是否导出为 CSV 或 JSON？"，带一键按钮与关闭 |

### 6.2 修改文件

- **`pages/Home.tsx`**：
  - 删除原本散落的 `handleExportCSV/exportToCSV/...` 内联逻辑，统一为 `handleExport(format)`（客户端导出已加载结果）与 `handleQuickExport(format)`（走后端一键导出）。
  - 查询成功且 `rowCount > 0` 时 `setShowExportPrompt(true)`，在结果卡片顶部渲染 `ExportPrompt`。
  - 结果卡片右上角用 `ExportButtons`；SQL 编辑器右上角新增 `EXPORT` 下拉（一键"执行+导出"，无需先点 Execute）。
  - 超过 1 万行时弹出大结果集确认框。
- **`components/ResultTable.tsx`**：工具栏内置 `ExportButtons`，所有使用该组件的页面（如 `pages/queries/execute.tsx`）自动获得导出能力。

### 6.3 交互效果

1. 用户执行 SQL → 成功返回数据。
2. 结果区顶部出现黄色 AI 提示条："AI Assistant: Your query returned N rows. Would you like to export as CSV or JSON?"
3. 点击 `Export CSV` / `Export JSON` 立即下载；也可点结果卡片右上角按钮，或编辑器右上角 `EXPORT` 下拉一键执行并下载。
4. 下载文件名形如 `mydb_query_20260422T103000Z.csv`。

## 7. 自动化工作流（Agent / Command / CLI）

### 7.1 Claude Code 自定义命令

`.claude/commands/export-query.md` 定义 `/export-query` 斜杠命令，参数为 `<database-name> "<SQL>" [csv|json]`，明确 5 步工作流（识别目标 → 校验只读 → 调用 `/export` → 校验输出 → 汇总），并给出 curl 示例：
```bash
curl -X POST http://localhost:8000/api/v1/dbs/mydb/export \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT id, name FROM users LIMIT 100","format":"csv"}' \
  -o users.csv
```

### 7.2 Cursor 规则

`.cursor/rules/export-feature.mdc` 在涉及导出相关文件时自动加载，把"导出数据"任务分解为 5 个子任务，并约束：只读、BOM、必须写测试、保持 camelCase。

### 7.3 CLI 脚本

`backend/scripts/export_query.py` 提供命令行一键导出，既可调用运行中的后端（HTTP 模式，仅用标准库），也可 `--standalone` 在进程内直连数据库：
```bash
python scripts/export_query.py mydb "SELECT id, name FROM users LIMIT 10" --format csv --out ./exports
python scripts/export_query.py postgresql://... "SELECT 1" --standalone --format json
```

## 8. 接口示例

请求：
```http
POST /api/v1/dbs/interview/export
Content-Type: application/json

{ "sql": "SELECT id, name FROM candidates ORDER BY id LIMIT 3", "format": "json" }
```

JSON 响应体：
```json
{
  "metadata": {
    "database": "interview",
    "generatedAt": "2026-04-22T10:30:00.123456+00:00",
    "rowCount": 3,
    "executionTimeMs": 8,
    "sql": "SELECT id, name FROM candidates ORDER BY id LIMIT 3",
    "columns": [
      { "name": "id", "dataType": "integer" },
      { "name": "name", "dataType": "character varying" }
    ]
  },
  "rows": [
    { "id": 1, "name": "Alice" },
    { "id": 2, "name": "Bob, Jr." },
    { "id": 3, "name": null }
  ]
}
```

CSV 响应（文本，首字节为 BOM）：
```
id,name
1,Alice
2,"Bob, Jr."
3,
```

## 9. 验证方法

### 9.1 后端单元测试
```bash
cd backend
uv run pytest tests/unit/test_export.py -v
```

### 9.2 手动验证（后端 + 前端）
```bash
make dev            # 启动后端 :8000 与前端 :5173
```
1. 在界面注册一个 PostgreSQL/MySQL 连接并刷新元数据；
2. 执行 `SELECT ...`，确认出现 AI 导出提示；
3. 分别点击 CSV / JSON，验证文件下载且 Excel 打开 CSV 不乱码；
4. 使用编辑器右上角 `EXPORT` 下拉，验证"一键执行+导出"；
5. 用 curl 或 CLI 脚本调用 `/export`，验证自动化链路。

### 9.3 自动化验证
```bash
# HTTP 模式（后端需在运行）
python backend/scripts/export_query.py mydb "SELECT count(*) FROM users" --format json

# Claude Code 中
/export-query mydb "SELECT * FROM users LIMIT 100" csv
```

## 10. 改动文件清单

**新增**
- `backend/app/services/export.py`
- `backend/tests/unit/test_export.py`
- `backend/scripts/export_query.py`
- `frontend/src/services/export.ts`
- `frontend/src/components/ExportButtons.tsx`
- `frontend/src/components/ExportPrompt.tsx`
- `.claude/commands/export-query.md`
- `.cursor/rules/export-feature.mdc`
- `FEATURE_EXPORT.md`（本文档）

**修改**
- `backend/app/models/schemas.py`（新增 `ExportRequest`）
- `backend/app/api/v1/queries.py`（新增 `/export` 接口）
- `frontend/src/pages/Home.tsx`（接入主动提示、复用组件、一键导出）
- `frontend/src/components/ResultTable.tsx`（内置导出按钮）

## 11. 设计亮点

- **复用而非重复造轮子**：导出接口完全复用查询校验、连接池、历史记录，不新增数据库连接路径。
- **前后端双路径**：界面内即时导出（零请求）+ 服务端一键导出（适合 Agent/脚本）。
- **纯函数核心**：序列化逻辑独立成纯函数，单元测试无需启动 FastAPI 或数据库。
- **工程细节**：CSV BOM、RFC 4180 换行、JSON 日期安全序列化、大结果集确认、确定性文件名。
- **AI 原生交互**：查询后主动询问导出，贴合作业要求；同时用 Claude 命令 + Cursor 规则 + CLI 三种方式覆盖自动化场景。
