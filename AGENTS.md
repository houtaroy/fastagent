# AGENTS.md

## 项目概览

FastAgent 是一个 Python 3.13 FastAPI 服务，使用 OpenAI Agents SDK，并通过 SQLModel/SQLAlchemy 持久化 Agent 会话。

核心行为：

- 应用启动时创建数据库表。
- 从环境配置初始化 `AsyncOpenAI` 客户端。
- 在 `app.state.agent` 上注册单个 OpenAI Agent。
- 通过 Server-Sent Events 提供符合 AG-UI 协议的会话聊天流式接口。
- 提供已持久化 Agent 消息的分页查询接口。

## 仓库结构

- `app/main.py`：FastAPI 应用入口和 lifespan 初始化逻辑。
- `app/api/main.py`：API 路由组合。
- `app/api/routes/session.py`：会话聊天和消息查询路由。
- `app/api/deps.py`：FastAPI 依赖注入辅助函数。
- `app/ag_ui/adapter.py`：将 OpenAI Agents SDK 流事件转换为 AG-UI 事件。
- `app/core/config.py`：基于环境变量的配置。
- `app/core/db.py`：异步 SQLAlchemy engine/session 和建表初始化。
- `app/models.py`：SQLModel 表模型和 API schema。
- `app/agent/tools.py`：Agent 工具函数。

## 环境配置

配置通过 `pydantic-settings` 从 `.env` 加载。

重要变量：

- `DATABASE_URI`：异步 SQLAlchemy 数据库 URI。默认使用 PostgreSQL 和 `asyncpg`。
- `OPENAI_BASE_URL`：可选的 OpenAI 兼容接口地址。
- `OPENAI_API_KEY`：OpenAI API key。
- `OPENAI_TRACING`：是否启用 OpenAI Agents tracing。
- `AGENT_NAME`：运行时 Agent 名称。
- `AGENT_MODEL`：运行时 Agent 模型。

`.env.example` 是公开模板。不要提交 `.env` 中的密钥。

## 常用命令

本项目优先使用 `uv`。

```bash
uv sync
uv run fastapi dev app/main.py
uv run ruff check .
uv run mypy .
uv run ty check
```

当前仓库还没有专门的测试套件。

## 编码约定

- 保持与现有小模块 FastAPI 结构一致。
- 优先为函数添加类型标注和明确返回类型，尤其是依赖函数和路由处理函数。
- 数据库支持的 API 数据优先使用 SQLModel 模型，除非明确需要更窄的 schema。
- 数据库访问使用异步 SQLAlchemy session。
- 序列化 Agent 消息时保留非 ASCII 内容。
- AG-UI SSE 事件必须按协议输出 camelCase alias 字段；使用 `ServerSentEvent(raw_data=event.model_dump_json(by_alias=True, exclude_none=True))`，避免通过 `data=` 触发默认 snake_case 序列化。
- 除非请求所需，否则避免大范围重构。

## API 说明

`POST /sessions/{id}/chat`

- 接收包含 `content` 的 `ChatCreate`。
- 将 OpenAI Agents SDK 响应事件转换为 AG-UI 事件，并以 SSE 形式流式返回。
- SSE `data` 内容使用 AG-UI camelCase 字段，例如 `threadId`、`runId`、`messageId`、`toolCallId`。
- 使用 `SQLAlchemySession(session_id=id, engine=async_engine, ensure_ascii=False)` 持久化会话。

`GET /sessions/{id}/messages`

- 支持 cursor 分页：数据库查询按倒序取数，再反转为时间正序返回。
- `cursor` 表示查询小于该消息 id 的更早消息。
- `limit` 限制为 `1..100`。

## 数据库说明

- 启动时调用 `SQLModel.metadata.create_all`。
- `agent_sessions.session_id` 是主键。
- `agent_messages.session_id` 删除时级联。
- `agent_messages.id` 是自增整数主键。

修改持久化行为时，需要确认与 OpenAI Agents SDK `SQLAlchemySession` 的预期兼容。
