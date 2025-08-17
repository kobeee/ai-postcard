# Lovart.ai 模拟器前端

## 技术栈
- Vue 3 + Vite
- marked.js (Markdown 渲染)
- highlight.js (代码高亮)

## 目录结构
```
src/ai-agent-service/app/frontend/
├─ src/
│   ├─ components/
│   │   ├─ MarkdownView.vue    # Markdown渲染组件
│   │   └─ CodeView.vue        # 代码高亮组件
│   ├─ App.vue                 # 主应用
│   ├─ main.js                 # 入口文件
│   └─ style.css              # 全局样式
├─ public/                     # 静态资源
├─ package.json               # 前端依赖配置
├─ vite.config.js            # Vite配置
└─ index.html                # HTML模板
```

## 开发模式

### 1. 容器内开发（推荐）
```bash
# 启动ai-agent-service容器（包含前端构建）
sh scripts/dev.sh up agent

# 访问 http://localhost:8080 查看应用
```

### 2. 本地前端开发
```bash
# 进入前端目录
cd src/ai-agent-service/app/frontend

# 安装依赖
npm install

# 启动开发服务器（代理到后端API）
npm run dev

# 访问 http://localhost:5173 查看应用
```

## 构建部署
```bash
# 构建前端到../static目录
npm run build

# 构建产物会自动被FastAPI静态文件服务托管
```

## API对接
- 前端通过 `/api/v1/coding/generate-code` 创建任务
- 通过 WebSocket `/api/v1/coding/status/{task_id}` 接收流式响应
- 支持的消息类型：
  - `markdown`: AI思考过程，用MarkdownView渲染
  - `code`: 代码内容，用CodeView高亮显示
  - `error`: 错误信息，高亮显示
  - `status`: 状态信息
  - `complete`: 生成完成

## 主要功能
- ✅ Markdown格式的AI思考过程实时渲染
- ✅ 代码高亮和网页预览双标签页
- ✅ 流式输出、错误高亮、状态指示
- ✅ WebSocket连接状态监控
- ✅ 响应式设计，现代化UI

## 热更新支持
- 前端源码修改后，容器内会自动重新构建并刷新
- 后端API修改后，FastAPI自动重载
- 实现真正的前后端分离开发体验
