# syntax=docker/dockerfile:1.6
# =============================================================================
# User Service - 统一 Dockerfile
# =============================================================================
# 用户服务，基于共用基础镜像构建
# =============================================================================

# 阶段1: 依赖构建
FROM python:3.11-slim as deps-builder

# 安装构建依赖（包括PostgreSQL客户端）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并安装Python依赖
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# =============================================================================
# 阶段2: 运行时镜像
# =============================================================================
FROM ai-postcard-base:latest as runtime

# 运行时使用 root
USER root
# 安装运行时PostgreSQL客户端库
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=deps-builder /opt/venv /opt/venv

# 复制应用代码
COPY . /app/

# 复制启动脚本并设置权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["/app/docker-entrypoint.sh"]