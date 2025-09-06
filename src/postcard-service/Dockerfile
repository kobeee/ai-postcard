# syntax=docker/dockerfile:1.6
# =============================================================================
# Postcard Service - 生产环境 Dockerfile
# =============================================================================
# 轻量级Python FastAPI服务，优化启动时间和镜像大小
# =============================================================================

# 阶段1: 依赖构建
FROM python:3.11-slim as builder

# 安装构建依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并安装依赖
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# =============================================================================
# 阶段2: 运行时环境
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
    BUILD_ENV=${BUILD_ENV}

# 安装运行时依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -g ${GROUP_ID} appuser \
    && useradd -u ${USER_ID} -g appuser -m -s /bin/bash appuser

# 设置工作目录
WORKDIR /app

# 创建必要目录
RUN mkdir -p /app/logs \
    && chown -R appuser:appuser /app

# 从构建阶段复制虚拟环境
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

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
