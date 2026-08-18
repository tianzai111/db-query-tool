# Database Query Tool

A web-based tool for managing PostgreSQL database connections, viewing metadata, and executing SQL queries with natural language support.

## Project Structure

```
w2/db_query/
├── backend/          # FastAPI backend (Python 3.12+)
├── frontend/         # React frontend (TypeScript, Refine 5)
├── fixtures/         # REST Client test files
│   ├── test.rest     # API test requests
│   └── README.md     # Testing guide
└── Makefile          # Development commands
```

## Quick Start

### Initial Setup

```bash
# Install all dependencies
make install

# Setup database and environment
make setup
# Then edit backend/.env and add your OPENAI_API_KEY

# Start development servers
make dev
```

### Development Commands

```bash
# View all available commands
make help

# Start backend only
make dev-backend

# Start frontend only
make dev-frontend

# Run tests
make test

# Format code
make format

# Run linters
make lint
```

## API Testing

### Using REST Client (VSCode)

1. Install [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. Open `fixtures/test.rest`
3. Click "Send Request" above any HTTP request
4. View responses in VSCode panel

See `fixtures/README.md` for detailed testing guide.

### Using Makefile

```bash
# Check if backend is running
make health

# Open API documentation
make docs
```

## Phase 1 Status

✅ **Phase 1 Complete**: All setup and foundation tasks completed.

- Backend project structure initialized
- Frontend project structure initialized
- Core infrastructure (FastAPI, database, models) ready
- Data models defined with camelCase API convention
- Makefile with common development tasks
- REST Client test file for API testing

## Next Steps

Proceed to Phase 2 for core feature implementation (US1 + US2).

---

## 数据导出功能模块（Data Export Feature）

本仓库在原始智能数据库查询工具基础上新增了数据导出功能模块，支持 CSV / JSON 两种格式，并提供"执行 + 导出"一键自动化。设计思路见 **[FEATURE_EXPORT.md](FEATURE_EXPORT.md)**。

- 后端：`backend/app/services/export.py`（纯函数序列化，CSV 带 UTF-8 BOM）
- 接口：`POST /api/v1/dbs/{name}/export`，单次请求完成 SQL 执行与文件下载
- 前端：`frontend/src/components/ExportButtons.tsx`、`ExportPrompt.tsx`（查询后 AI 助手主动询问导出）
- 自动化：`.claude/commands/export-query.md`、`.cursor/rules/export-feature.mdc`、`backend/scripts/export_query.py`

## 零安装演示环境（SQLite）

无需安装 PostgreSQL/MySQL 或 Node.js 即可体验完整的查询 + 导出流程。项目内置了一个 SQLite 适配器（Python 自带）和中文示例数据。

### Windows 一键启动

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

脚本会自动创建虚拟环境、安装后端依赖、生成并注册演示数据库 `demo`，然后启动后端（http://localhost:8000）。若检测到 npm，也会同时启动 React 前端（http://localhost:5173）。

### 手动启动后端

```bash
cd backend
pip install -e .                      # 或安装 pyproject.toml 中的依赖
python scripts/setup_demo.py          # 生成 demo.db 并注册连接、缓存元数据
uvicorn app.main:app --port 8000
```

随后：

- 打开在线 API 文档并直接试用：http://localhost:8000/docs
- 或打开随附的独立演示页（无需 Node）：在项目根目录执行 `python -m http.server 5173`，再访问 http://127.0.0.1:5173/demo-ui.html

### 通过命令行一键导出（自动化）

```bash
# HTTP 模式（后端需在运行）
python backend/scripts/export_query.py demo \
  "SELECT e.name, d.name AS department FROM employees e JOIN departments d ON e.department_id=d.id" \
  --format csv --out ./exports
```

演示库包含 `departments`（5）、`employees`（10）、`salaries`（13）三张表，含中文部门/姓名数据，可验证 CSV 在 Excel 中不乱码。
