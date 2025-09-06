# syntax=docker/dockerfile:1.6
# =============================================================================
# AI Agent Service - 统一 Dockerfile
# =============================================================================
# 复杂服务：Python + Node.js + Claude Code CLI + Puppeteer + 前端构建
# 基于共用基础镜像，多阶段构建优化
# =============================================================================

# 阶段1: Node.js 前端构建
FROM node:20-slim as frontend-builder

# 设置工作目录
WORKDIR /build

# 复制前端package文件并安装依赖（利用Docker层缓存）
COPY app/frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --include=dev --prefer-offline --no-audit --progress=false

# 复制前端源码并构建
COPY app/frontend/ ./
RUN --mount=type=cache,target=/root/.npm \
    npm run build

# =============================================================================
# 阶段2: Python依赖构建
# =============================================================================
FROM python:3.11-slim as deps-builder

# 安装构建依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并安装Python依赖
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# =============================================================================
# 阶段3: 运行时镜像
# =============================================================================
FROM ai-postcard-base:latest as runtime

# 运行时使用 root
USER root
# 安装Node.js和系统依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    chromium \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 配置Puppeteer使用系统Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# 配置npm的健壮性设置
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 10000 \
    && npm config set fetch-retry-maxtimeout 600000

# 安装全局Node.js包
RUN --mount=type=cache,target=/root/.npm \
    npm install -g --no-audit --progress=false @anthropic-ai/claude-code puppeteer

# 创建AI Agent特有目录
RUN mkdir -p \
    /app/app/static/generated \
    /app/app/static/assets \
    /app/app/frontend/dist

# 切换到root以执行复制与授权
USER root

# 从构建阶段复制Python虚拟环境
COPY --from=deps-builder /opt/venv /opt/venv

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /build/dist /app/app/frontend/dist

# 复制应用代码
COPY . /app/

# 复制启动脚本并设置权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["/app/docker-entrypoint.sh"]