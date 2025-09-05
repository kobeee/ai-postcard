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

# 构建前端应用
COPY app/frontend/package*.json ./frontend/
RUN cd frontend && npm ci --include=dev

COPY app/frontend/ ./frontend/
RUN cd frontend && npm run build

# =============================================================================
# 阶段2: Python依赖构建
# =============================================================================
FROM python:3.11-slim as python-builder

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /build

# 创建虚拟环境并安装Python依赖
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# =============================================================================
# 阶段3: 运行时环境
# =============================================================================
FROM python:3.11-slim as runtime

# 构建参数
ARG BUILD_ENV=production
ARG USER_ID=1000
ARG GROUP_ID=1000

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    NODE_ENV=production \
    BUILD_ENV=${BUILD_ENV}

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y \
    # Node.js 18 LTS
    curl \
    gnupg \
    ca-certificates \
    # Puppeteer依赖
    chromium \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    wget \
    xdg-utils \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户和组
RUN groupadd -g ${GROUP_ID} appuser \
    && useradd -u ${USER_ID} -g appuser -m -s /bin/bash appuser

# 设置Puppeteer使用系统Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# 安装全局Node.js包
RUN npm install -g @anthropic-ai/claude-code puppeteer

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