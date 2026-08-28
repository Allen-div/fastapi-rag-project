# RAG 对话系统 - 前端

基于 Vue 3 + Vite 构建的 RAG 对话系统前端，支持 AI 对话、文档上传和管理。

## 技术栈

- Vue 3 (Composition API + `<script setup>`)
- Vue Router 4
- Pinia 状态管理
- Axios HTTP 请求
- Vite 5 构建工具
- 纯 CSS 样式（无 UI 框架依赖）

## 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.js
    ├── App.vue
    ├── style.css
    ├── router/
    │   └── index.js
    ├── stores/
    │   └── auth.js
    ├── utils/
    │   └── api.js
    └── views/
        ├── Login.vue
        ├── Register.vue
        ├── Chat.vue
        └── admin/
            ├── Upload.vue
            └── Documents.vue
```

## 本地启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

服务默认运行在 `http://localhost:3000`。

### 3. 确保后端服务已启动

后端需要运行在 `http://localhost:8000`（Vite 已配置代理，前端请求 `/api/*` 会自动转发到后端）。

## 路由与测试

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 输入用户名密码登录 |
| `/register` | 注册 | 创建新账号 |
| `/chat` | 对话 | 左侧对话列表 + 右侧 SSE 流式聊天 |
| `/admin/upload` | 上传文档 | 拖拽/点击上传文件 |
| `/admin/documents` | 文档管理 | 查看、分页、删除已上传文档 |

### 测试流程

1. 访问 `http://localhost:3000`，自动跳转到 `/login`
2. 如果没有账号，点击"立即注册"跳转到 `/register` 注册
3. 登录后进入 `/chat` 对话页面
4. 点击顶部导航"管理"进入 `/admin/upload` 上传文档
5. 上传完成后到 `/admin/documents` 查看文档列表
6. 回到 `/chat`，在输入框提问，AI 将基于上传的文档回答

## 后端 API 对接

前端通过 Vite proxy 将 `/api` 请求转发到 `http://localhost:8000`：

- `POST /api/auth/login` - 登录（OAuth2 表单格式）
- `POST /api/auth/register` - 注册
- `POST /api/chat/stream` - SSE 流式对话
- `GET /api/chat/conversation` - 对话列表
- `POST /api/document/upload` - 上传文档（multipart）
- `GET /api/document/documents` - 文档列表
- `DELETE /api/document/documents/{id}` - 删除文档

## 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录，可直接部署到 Nginx 等静态服务器。