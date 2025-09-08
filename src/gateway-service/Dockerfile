# syntax=docker/dockerfile:1.6
# =============================================================================
# Gateway Service - 统一 Dockerfile
# =============================================================================
# API 网关服务，基于共用基础镜像构建
# =============================================================================

# 阶段1: 依赖构建
FROM python:3.11-slim as deps-builder

# 配置 APT 镜像与网络参数（国内镜像 + IPv4）
RUN set -eux; \
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99network && \
    sed -ri 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g; s|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list || true

# 安装构建依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并安装Python依赖
WORKDIR /build
COPY requirements.txt .

# 配置pip镜像源以优化网络连接和增强稳定性
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && /opt/venv/bin/pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn \
    && /opt/venv/bin/pip config set global.extra-index-url https://mirrors.aliyun.com/pypi/simple \
    && /opt/venv/bin/pip config set global.timeout 120 \
    && /opt/venv/bin/pip config set global.retries 10 \
    && /opt/venv/bin/pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

# =============================================================================
# 阶段2: 运行时镜像
# =============================================================================
FROM ai-postcard-base:latest as runtime

# 运行时使用 root
USER root
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
