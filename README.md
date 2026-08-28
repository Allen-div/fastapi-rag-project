# FastAPI RAG Project

基于 FastAPI 的 RAG（检索增强生成）对话系统，支持文档上传、向量化存储、语义检索和流式 AI 对话。

## 功能特性

- **用户认证**：JWT 注册/登录，OAuth2 密码流
- **文档管理**：上传、列表、删除，自动编码检测（支持 GBK/UTF-8 等）
- **RAG 对话**：基于上传文档的智能问答，流式 SSE 推送
- **向量检索**：Milvus 存储，COSINE 相似度搜索，IVF_FLAT 索引
- **对话历史**：多轮对话支持，thread_id 关联，历史消息自动截断
- **Agent 架构**：LangGraph Agent + before_model 中间件，可扩展工具调用

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 关系数据库 | MySQL 8.x + SQLAlchemy 2.0 (aiomysql 异步驱动) |
| 向量数据库 | Milvus (pymilvus MilvusClient) |
| 大模型 | 阿里云百炼 - deepseek-v4-flash (对话) / text-embedding-v3 (嵌入) |
| Agent 框架 | LangChain + LangGraph |
| 认证 | JWT (python-jose + bcrypt) |
| 数据库迁移 | Alembic |
| 缓存 | Redis (已配置，待启用) |

## 环境要求

- Python 3.13+
- MySQL 8.0+
- Milvus 2.3+
- Redis 6.0+ (可选)

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd fastapi_rag_project
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env` 文件并修改配置：

```bash
cp .env.example .env  # 或直接编辑 .env
```

关键配置项：

```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=23307
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=fast_rag

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 阿里云百炼
ALIYUN_API_KEY=sk-your-api-key
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ALIYUN_MODEL=deepseek-v4-flash
ALIYUN_EMBEDDING_MODEL=text-embedding-v3

# 应用
SECRET_KEY=your-secret-key
DEBUG=True
```

### 4. 初始化数据库

确保 MySQL 已创建对应数据库，然后运行 Alembic 迁移：

```bash
alembic upgrade head
```

### 5. 启动服务

```bash
python run.py
```

服务默认运行在 `http://0.0.0.0:8000`。

## API 接口

### 健康检查

```
GET /health
```

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录（返回 JWT Token） |

### 文档管理（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/document/upload` | 上传文档（multipart/form-data） |
| GET | `/api/document/documents?page=1&page_size=10` | 文档列表 |
| DELETE | `/api/document/documents/{document_id}` | 删除文档 |

### 对话（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | SSE 流式对话 |
| GET | `/api/chat/conversation?page=1&page_size=10` | 对话列表 |

### 对话请求示例

```json
POST /api/chat/stream
Authorization: Bearer <token>

{
  "query": "这份文档的主要内容是什么？",
  "thread_id": null,
  "top_k": 5
}
```

- `thread_id` 为 `null` 时创建新对话，传入已有 ID 则继续该对话
- 响应为 SSE 事件流，事件类型：`ai_content`（AI 回复片段）、`done`（完成信号）

## 项目结构

```
fastapi_rag_project/
├── run.py                          # 启动入口
├── requirements.txt                # 依赖列表
├── alembic.ini                     # Alembic 配置
├── .env                            # 环境变量
├── app/
│   ├── main.py                     # FastAPI 应用实例
│   ├── core/
│   │   ├── config.py               # 配置管理（pydantic-settings）
│   │   ├── database.py             # 异步引擎 & Session 工厂
│   │   ├── security.py             # JWT 工具 & 密码哈希
│   │   ├── dependencies.py         # 认证依赖注入
│   │   └── system_prompt.py        # RAG 系统提示词
│   ├── models/
│   │   ├── user.py                 # User ORM
│   │   ├── chat.py                 # Conversation & Message ORM
│   │   └── document.py             # Document ORM
│   ├── schemas/
│   │   ├── user.py                 # 用户请求/响应模型
│   │   ├── chat.py                 # 对话请求/响应模型
│   │   └── document.py             # 文档响应模型
│   ├── api/
│   │   ├── router.py               # 路由聚合
│   │   ├── auth.py                 # 认证接口
│   │   ├── chat.py                 # 对话接口
│   │   └── document.py             # 文档接口
│   ├── services/
│   │   ├── rag_service.py          # RAG 核心逻辑
│   │   ├── vector_service.py       # Milvus 向量操作
│   │   ├── llm_service.py          # LLM & Embedding & Agent
│   │   ├── chat_history_service.py # 对话历史 CRUD
│   │   ├── user_service.py         # 用户 CRUD
│   │   └── agent_middleware.py     # Agent 中间件
│   └── utils/
│       └── utils.py                # 文件编码检测
├── alembic/
│    └── versions/                   # 迁移脚本
└── frontend                         # 前端代码

```

## 数据流

```
用户上传文档
    ↓
自动编码检测 (chardet)
    ↓
文本分块 (500字符 + 50重叠)
    ↓
DashScope text-embedding-v3 向量化 (1024维)
    ↓
┌─────────────┬─────────────┐
│   Milvus    │   MySQL     │
│ (向量+文本)  │ (文档元信息) │
└─────────────┴─────────────┘

用户提问
    ↓
查询向量化 → Milvus 检索 Top-K 相似片段
    ↓
构建 Prompt (系统提示 + 参考文档 + 用户问题)
    ↓
LangGraph Agent 流式生成 → SSE 推送前端
    ↓
保存对话记录到 MySQL
```

## Milvus 集合结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT64 (PK, auto) | 主键 |
| vector | FLOAT_VECTOR(1024) | 文本向量 |
| text | VARCHAR(65535) | 原始文本 |
| metadata | JSON | 元数据 (user_id, file_name, chunk_index) |
| doc_id | VARCHAR(100) | 文档唯一标识 |

索引类型：IVF_FLAT，度量方式：COSINE。

## 数据库表

| 表名 | 说明 |
|------|------|
| users | 用户信息 |
| conversations | 对话会话，通过 thread_id 关联 LangGraph 状态 |
| messages | 对话消息 (user/assistant/tool) |
| documents | 上传文档元信息，通过 vector_id 关联 Milvus |

## License

MIT

## 前端
### 本地启动
cd frontend

npm install

npm run dev

访问 http://localhost:3000，自动跳转登录页。
