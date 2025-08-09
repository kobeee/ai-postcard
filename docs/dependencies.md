# 依赖管理说明

## 概述

本项目使用多种技术栈，每个服务都有自己的依赖管理文件。由于部分服务的技术栈尚未最终确定，我们为每个服务提供了多个技术栈的依赖模板。

## 服务依赖概览

### AI Agent Service (Python/FastAPI - 已确定)
- **依赖文件**: `src/ai-agent-service/requirements.txt`
- **技术栈**: Python 3.10 + FastAPI
- **核心依赖**:
  - FastAPI + Uvicorn (Web 框架)
  - SQLAlchemy + Alembic (数据库 ORM)
  - OpenAI + LangChain (AI 集成)
  - Redis (缓存)
  - Pillow + OpenCV (图像处理)

### Gateway Service (Node.js/Express - 已确定)
- **依赖文件**: `src/gateway-service/package.json`
- **技术栈**: Node.js 18 + Express
- **核心依赖**:
  - Express (Web 框架)
  - http-proxy-middleware (代理中间件)
  - JWT + bcryptjs (认证)
  - Redis + PostgreSQL 客户端
  - 开发工具 (nodemon, jest, eslint)

### User Service (技术栈待定)
- **依赖文件**: 
  - `src/user-service/requirements.txt` (Python 版本)
  - `src/user-service/package.json` (Node.js 版本)
- **说明**: 提供了 Python 和 Node.js 两个版本的依赖模板，后续根据实际选择删除不需要的版本

### Postcard Service (技术栈待定)
- **依赖文件**: 
  - `src/postcard-service/requirements.txt` (Python 版本)
  - `src/postcard-service/package.json` (Node.js 版本)
- **说明**: 提供了 Python 和 Node.js 两个版本的依赖模板，包含图像处理相关库

## 依赖安装指南

### Python 服务 (推荐使用虚拟环境)

```bash
# 进入服务目录
cd src/ai-agent-service

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖 (如果需要)
pip install -r requirements-dev.txt  # 如果存在
```

### Node.js 服务

```bash
# 进入服务目录
cd src/gateway-service

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

## 开发环境自动化

使用提供的脚本可以自动处理依赖安装：

```bash
# 自动初始化所有服务的开发环境
sh scripts/setup-dev-env.sh
```

此脚本会：
1. 检查必要工具是否安装
2. 为 Python 服务创建虚拟环境
3. 自动安装 Node.js 和 Python 依赖
4. 创建必要的配置文件

## 依赖更新策略

### 添加新依赖

**Python 服务**:
```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装新包
pip install <package_name>

# 更新 requirements.txt
pip freeze > requirements.txt
```

**Node.js 服务**:
```bash
# 安装并保存到 dependencies
npm install <package_name> --save

# 安装并保存到 devDependencies
npm install <package_name> --save-dev
```

### 依赖版本管理

- **Python**: 使用固定版本号 (如 `fastapi==0.104.1`)
- **Node.js**: 使用语义化版本范围 (如 `^4.18.2`)

### 安全更新

定期检查和更新依赖以修复安全漏洞：

```bash
# Python
pip-audit  # 需要安装 pip-audit

# Node.js
npm audit
npm audit fix
```

## 生产环境依赖

### Python 服务
生产环境的 Dockerfile 会安装 requirements.txt 中的所有依赖。开发相关的包（如 pytest, black）也会被安装，但不会影响运行时性能。

### Node.js 服务
生产环境的 Dockerfile 使用 `npm ci --only=production` 只安装生产依赖。

## 故障排除

### 常见问题

1. **Python 虚拟环境问题**
   ```bash
   # 删除并重新创建虚拟环境
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Node.js 依赖冲突**
   ```bash
   # 清理并重新安装
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **容器内依赖问题**
   ```bash
   # 重新构建镜像
   sh scripts/dev.sh up <service> --build
   ```

### 版本兼容性

- **Python**: 项目要求 Python 3.10+
- **Node.js**: 项目要求 Node.js 18+
- **npm**: 推荐使用 npm 8+

确保本地开发环境满足这些版本要求。
