#!/bin/bash

# =============================================================================
# AI Agent Service - Docker 容器启动脚本
# =============================================================================
# 功能：处理容器启动时的初始化和服务启动
# =============================================================================

set -e

# 颜色定义（仅在TTY时使用）
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 环境检查
check_environment() {
    log_info "检查环境配置..."
    
    # 检查关键环境变量
    local required_vars=(
        "ANTHROPIC_AUTH_TOKEN"
        "GEMINI_API_KEY"
        "DB_HOST"
        "REDIS_HOST"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_warning "缺少环境变量: ${missing_vars[*]}"
        log_warning "某些功能可能无法正常工作"
    else
        log_success "环境变量检查通过"
    fi
}

# 目录权限检查
check_permissions() {
    log_info "检查目录权限..."
    
    local dirs=(
        "/app/app/static/generated"
        "/app/app/static/assets"
        "/app/logs"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -w "$dir" ]; then
            log_warning "目录不可写: $dir"
            # 尝试创建目录（如果不存在）
            mkdir -p "$dir" 2>/dev/null || true
        fi
    done
    
    log_success "目录权限检查完成"
}

# 等待依赖服务
wait_for_services() {
    log_info "等待依赖服务启动..."
    
    # 等待PostgreSQL
    if [ -n "$DB_HOST" ]; then
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port='${DB_PORT:-5432}',
        database='${DB_NAME:-ai_postcard}',
        user='${DB_USER:-postgres}',
        password='$DB_PASSWORD'
    )
    conn.close()
    print('Connected')
except:
    exit(1)
" 2>/dev/null; then
                log_success "PostgreSQL 连接成功"
                break
            fi
            
            log_info "等待 PostgreSQL ($attempt/$max_attempts)..."
            sleep 2
            attempt=$((attempt + 1))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_warning "PostgreSQL 连接超时，但继续启动"
        fi
    fi
    
    # 等待Redis
    if [ -n "$REDIS_HOST" ]; then
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if python -c "
import redis
import os
try:
    r = redis.Redis(
        host='$REDIS_HOST',
        port=${REDIS_PORT:-6379},
        password='$REDIS_PASSWORD'
    )
    r.ping()
    print('Connected')
except:
    exit(1)
" 2>/dev/null; then
                log_success "Redis 连接成功"
                break
            fi
            
            log_info "等待 Redis ($attempt/$max_attempts)..."
            sleep 2
            attempt=$((attempt + 1))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_warning "Redis 连接超时，但继续启动"
        fi
    fi
}

# 处理信号
cleanup() {
    log_info "接收到终止信号，正在关闭..."
    
    # 终止后台进程
    if [ -n "$UVICORN_PID" ]; then
        kill "$UVICORN_PID" 2>/dev/null || true
        wait "$UVICORN_PID" 2>/dev/null || true
    fi
    
    log_success "服务已关闭"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT SIGQUIT

# 主函数
main() {
    log_info "AI Agent Service 容器启动中..."
    log_info "工作模式: ${WORKER_MODE:-false}"
    
    # 环境检查
    check_environment
    check_permissions
    
    # 等待依赖服务
    if [ "${WORKER_MODE}" != "true" ]; then
        wait_for_services
    fi
    
    # 决定启动模式
    if [ "${WORKER_MODE}" = "true" ]; then
        log_info "启动 AI Agent Worker 进程..."
        exec python -m app.worker
    else
        # 检查是否传入了自定义命令
        if [ $# -gt 0 ]; then
            log_info "执行自定义命令: $*"
            exec "$@"
        else
            # 启动Web服务（统一使用 uvicorn）
            log_info "启动 AI Agent Web 服务..."
            exec uvicorn app.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --reload \
                --reload-dir app \
                --log-level info
        fi
    fi
}

# 执行主函数
main "$@"
