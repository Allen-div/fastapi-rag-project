# FastAPI RAG 智能对话系统 — 项目描述

## 一、项目概述

本项目是一个基于 **FastAPI + Vue 3** 的全栈 RAG（检索增强生成）智能对话系统。用户上传文档后，系统自动完成文本解析、向量化入库；用户在聊天界面提问时，系统通过语义检索从向量库召回相关片段，交给大模型生成带上下文的流式回答。前后端分离，支持多用户、多会话、文档全生命周期管理。

**项目定位**：一个开箱即用的企业级 RAG 应用脚手架，覆盖「文档接入 → 知识入库 → 智能问答 → 会话管理」完整闭环。

## 二、核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| 用户认证 | 注册 / 登录 / JWT | OAuth2 密码流，bcrypt 密码哈希，JWT 无状态鉴权 |
| 文档管理 | 上传 / 列表 / 删除 | 拖拽上传，自动编码检测（GBK/UTF-8 等），分页管理 |
| 知识入库 | 分块 → 向量化 → 入库 | 500 字符分块 + 50 重叠，DashScope 向量模型，Milvus 存储 |
| 智能问答 | RAG 检索增强生成 | Milvus 余弦相似度 Top-K 召回，LangGraph Agent 流式生成 |
| 流式输出 | SSE 逐字推送 | 打字机效果，前后端边生成边展示 |
| 会话管理 | 多轮对话 / 历史记录 | thread_id 关联 LangGraph 状态，历史消息自动截断 |
| 前端体验 | 左右分栏聊天 / 后台管理 | 用户消息右侧、AI 回复左侧，消息本地缓存免重复请求 |

## 三、技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite)               │
│   聊天页 / 登录注册 / 上传页 / 文档管理页            │
└───────────────┬─────────────────────────────────────┘
                │ HTTP / SSE (Vite Proxy 转发)
┌───────────────▼─────────────────────────────────────┐
│                 后端 (FastAPI)                       │
│   Auth ── Document ── Chat(SSE) ── UserInfo         │
│        │           │           │                    │
│   UserService   RAGService  LLMService / Agent      │
│        │           │           │                    │
│   SQLAlchemy    Milvus     LangGraph + DashScope    │
│   (async)       (向量库)    (Agent / 流式生成)      │
└─────────────────────────────────────────────────────┘
```

### 技术栈明细

| 分层 | 组件 | 用途 |
|------|------|------|
| 前端框架 | Vue 3 + Vite + Pinia + Vue Router | 组件化 SPA，Composition API |
| 前端请求 | Axios + fetch(SSE) | REST 调用 + 流式读取 |
| 后端框架 | FastAPI + Uvicorn | 高性能异步 Web 框架 |
| 关系库 | MySQL 8 + SQLAlchemy 2.0 + asyncmy/aiomysql | 用户/文档/会话/消息持久化 |
| 向量库 | Milvus + pymilvus | 文本向量存储与相似度检索 |
| 大模型 | 阿里云百炼 deepseek-v4-flash | 对话生成 |
| 向量模型 | 阿里云百炼 text-embedding-v3 | 文本向量化（1024 维） |
| Agent 框架 | LangChain + LangGraph | Agent 编排、状态管理、中间件 |
| 认证 | python-jose + bcrypt | JWT 签发与校验 |
| 迁移 | Alembic | 数据库版本管理 |

## 四、系统设计

### 数据流 — 文档入库

```
用户上传文档
   ↓
自动编码检测 (chardet)
   ↓
文本分块 (500 字符 + 50 重叠)
   ↓
text-embedding-v3 向量化 (1024 维)
   ↓
┌──────────────┬──────────────┐
│   Milvus     │    MySQL     │
│ 向量 + 文本  │ 文档元信息    │
└──────────────┴──────────────┘
```

### 数据流 — 智能问答

```
用户提问
   ↓
查询向量化 → Milvus 检索 Top-K 相似片段
   ↓
构建 Prompt (系统提示 + 参考文档 + 用户问题)
   ↓
LangGraph Agent 流式生成 → SSE 逐字推送前端
   ↓
保存对话记录到 MySQL
```

### 后端分层

```
app/api/        路由层：auth / document / chat / user
app/schemas/    Pydantic 数据模型（请求/响应校验）
app/services/   业务层：RAG / 向量 / LLM / 会话历史 / Agent 中间件
app/models/     SQLAlchemy ORM 模型（User / Conversation / Message / Document）
app/core/       基础设施：配置 / 数据库引擎 / 安全认证 / 系统提示词
```

### 前端架构

```
frontend/
├── src/router/     路由 + 登录守卫
├── src/stores/     Pinia（认证状态、用户信息）
├── src/utils/      Axios 封装（自动带 Token、401 拦截）
└── src/views/
    ├── Chat.vue        对话页（左侧会话列表 + 右侧流式聊天）
    ├── Login / Register 认证页
    └── admin/          上传页 + 文档管理页
```

## 五、关键技术点

1. **流式对话**：后端 `agent.astream(stream_mode='messages')` 逐块 yield，SSE 格式推送；前端用 `fetch` + `ReadableStream` 解析，`reactive` 保证逐字渲染触发 Vue 响应式更新。

2. **Agent 架构**：基于 LangGraph 的 `create_agent`，通过 `before_model` 中间件处理历史消息，按 token 成本自动截断，可扩展工具调用。

3. **向量检索**：Milvus 集合设计 `id + vector(1024) + text + metadata + doc_id`，IVF_FLAT 索引、COSINE 度量，按 `user_id` 隔离文档实现多租户。

4. **多轮会话**：`thread_id` 贯穿 LangGraph 状态与 MySQL 会话记录，前端切换会话时命中本地缓存即秒开，不重复请求后端。

5. **前后端分离**：Vite Proxy 将 `/api` 转发至后端，避免跨域；JWT 存储于 localStorage，Axios 拦截器统一注入与 401 处理。

## 六、亮点与难点

**亮点**
- 完整的 RAG 闭环：从文档上传到向量化到智能问答，链路完整、可运维
- 异步全链路：aiomysql/asyncmy + 异步引擎，天然支撑高并发
- 优雅的流式体验：SSE + 打字机效果 + 自动滚动
- 用户/文档/会话三级数据隔离

**难点与解法**
- 大模型流式与 RAG 检索的时序编排 → 采用 LangGraph Agent 统一编排
- 多轮对话历史膨胀导致 token 超限 → 中间件截断策略
- 中文文档乱码 → chardet 自动编码检测
- 切换对话重复请求慢 → 前端消息缓存，命中本地直接展示
- 数据库查询链路慢 → 连接池调优、驱动选型（asyncmy）、关闭 SQL echo

## 七、运行方式

```bash
# 后端
pip install -r requirements.txt
alembic upgrade head        # 初始化数据库
python run.py               # http://localhost:8000

# 前端
cd frontend
npm install
npm run dev                 # http://localhost:3000
```

测试入口：注册 → 登录 → 管理页上传文档 → 聊天页提问。
