# Personal Life Assistant — Backend

FastAPI + SQLAlchemy + SQLite 后端，提供待办、记账、日程、日记、课表看板五个模块的 REST API。

完整接口契约见 [`../docs/API.md`](../docs/API.md)。运行后可访问：

- Swagger UI：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>

## 环境要求

- Python 3.11+
- 不需要单独安装 SQLite，Python 自带驱动

## 启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

首次启动会自动创建 `backend/data/life_assistant.db` 和全部数据表。

## 配置

通过环境变量或 `backend/.env` 覆盖默认配置，参考 [`.env.example`](.env.example)。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PLA_DATABASE_URL` | `sqlite:///.../backend/data/life_assistant.db` | SQLAlchemy 数据库 URL |
| `PLA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,null` | 逗号分隔的允许来源 |
| `PLA_DEBUG` | `false` | FastAPI debug 模式 |

打包后的 Electron 页面通过 `file://` 加载时，浏览器发送的 `Origin` 是 `null`，因此默认 CORS 列表包含 `null`。如果 Vue 开发服务器使用其他端口，需要相应追加来源。

## 测试

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

测试使用临时 SQLite 文件，不会改动开发数据库。

代码检查：

```bash
ruff check app tests
ruff format --check app tests
```

## 目录结构

```text
backend/
├── app/
│   ├── main.py           # 应用工厂、生命周期、CORS、系统接口
│   ├── config.py         # 环境配置
│   ├── database.py       # 引擎、Session、建表
│   ├── models.py         # SQLAlchemy 模型
│   ├── dependencies.py   # get_db 依赖
│   ├── timetable_parser.py # 课表 HTML 解析器
│   ├── schemas/          # Pydantic 请求/响应模型
│   └── routers/          # 五个业务模块路由
├── tests/
├── data/                 # SQLite 数据文件（已 gitignore）
└── requirements*.txt
```

## 当前设计决策

- **单用户、无鉴权**：仅用于本机个人应用，默认监听 `127.0.0.1`，不要暴露到公网。
- **UTC 存储**：时间以 UTC 入库，API 返回带时区的时间；前端负责把本地时间转换为 ISO 8601。
- **金额用整数分**：所有金额字段以 `_cents` 结尾，避免浮点精度问题。
- **同步 SQLAlchemy + SQLite**：本地单用户场景足够，代码更简单；后续如需高并发再评估异步或 PostgreSQL。
- **`create_all` 建表**：当前是初始开发阶段；引入前端联调、需要修改表结构时应增加 Alembic 迁移。
- **软删除未实现**：删除为物理删除，前端应提供确认操作。
- **课表只保存解析结果**：HTML 导入后不保留原始文件；解析失败或部分失败会通过 `warnings` 返回，需要更正源文件后重新导入。
