# syntax=docker/dockerfile:1.6
# =============================================================================
# AI Agent Service - 生产环境 Dockerfile
# =============================================================================
# 多阶段构建，优化镜像大小和安全性
# 包含：Python + Node.js + Claude Code CLI + Puppeteer + 前端构建
# =============================================================================

# 阶段1: 构建环境 - 包含所有构建工具
FROM node:20-slim as builder

# 设置构建参数
ARG BUILD_ENV=production
ARG NODE_ENV=production

# 安装系统依赖和构建工具
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /build

# 构建前端应用（使用 npm 缓存与确定性安装）
COPY app/frontend/package*.json ./frontend/
RUN --mount=type=cache,target=/root/.npm \
    cd frontend && npm ci --include=dev --prefer-offline --no-audit --progress=false

COPY app/frontend/ ./frontend/
RUN --mount=type=cache,target=/root/.npm \
    cd frontend && npm run build

# =============================================================================
# 阶段2: Python依赖构建
# =============================================================================
FROM python:3.11-slim as python-builder

# 安装构建依赖（apt 缓存 + 最小化）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /build

# 创建虚拟环境并安装Python依赖（pip 缓存 + 重试）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# =============================================================================
# 阶段3: 运行时环境
# =============================================================================
FROM python:3.11-slim as runtime

# 构建参数
ARG BUILD_ENV=production
ARG APP_UID=1000
ARG APP_GID=1000
ARG USER_ID=${APP_UID}
ARG GROUP_ID=${APP_GID}

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    NODE_ENV=production \
    BUILD_ENV=${BUILD_ENV}

# 安装运行时系统依赖（最小化：Chromium + 基础工具）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js（使用发行版源，避免外部脚本）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户和组
RUN groupadd -g ${GROUP_ID} appuser \
    && useradd -u ${USER_ID} -g appuser -m -s /bin/bash appuser

# 设置Puppeteer使用系统Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# npm 下载健壮性与缓存；安装必要的全局包
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 10000 \
    && npm config set fetch-retry-maxtimeout 600000
RUN --mount=type=cache,target=/root/.npm \
    npm install -g --no-audit --progress=false @anthropic-ai/claude-code puppeteer

# 设置工作目录
WORKDIR /app

# 创建必要的目录结构
RUN mkdir -p \
    /app/app/static/generated \
    /app/app/static/assets \
    /app/logs \
    /app/app/frontend/dist \
    && chown -R appuser:appuser /app

# 从构建阶段复制Python虚拟环境
COPY --from=python-builder --chown=appuser:appuser /opt/venv /opt/venv

# 从构建阶段复制前端构建产物
COPY --from=builder --chown=appuser:appuser /build/frontend/dist /app/app/frontend/dist

# 复制应用代码
COPY --chown=appuser:appuser . /app/

# 切换到非特权用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动脚本
COPY --chown=appuser:appuser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 默认启动命令
CMD ["/app/docker-entrypoint.sh"]
