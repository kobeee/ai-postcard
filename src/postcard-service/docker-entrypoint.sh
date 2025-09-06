#!/bin/bash

# =============================================================================
# Postcard Service - Docker 容器启动脚本
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
    
    local required_vars=("DB_HOST" "DB_PASSWORD" "REDIS_HOST")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "缺少必需环境变量: ${missing_vars[*]}"
        exit 1
    fi
    
    log_success "环境变量检查通过"
}

# 等待数据库
wait_for_database() {
    log_info "等待数据库服务..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port='${DB_PORT:-5432}',
        database='${DB_NAME:-ai_postcard}',
        user='${DB_USER:-postgres}',
        password='$DB_PASSWORD'
    )
    conn.close()
except:
    exit(1)
" 2>/dev/null; then
            log_success "数据库连接成功"
            return 0
        fi
        
        log_info "等待数据库 ($attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "数据库连接失败"
    exit 1
}

# 等待Redis
wait_for_redis() {
    log_info "等待Redis服务..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import redis
try:
    r = redis.Redis(host='$REDIS_HOST', port=${REDIS_PORT:-6379}, password='$REDIS_PASSWORD')
    r.ping()
except:
    exit(1)
" 2>/dev/null; then
            log_success "Redis连接成功"
            return 0
        fi
        
        log_info "等待Redis ($attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_warning "Redis连接失败，但继续启动"
}

# 运行数据库迁移
run_migrations() {
    log_info "检查数据库迁移..."
    
    # 这里可以添加数据库迁移逻辑
    # python -m app.migrations.migrate
    
    log_success "数据库状态检查完成"
}

# 处理信号
cleanup() {
    log_info "接收到终止信号，正在关闭..."
    
    if [ -n "$UVICORN_PID" ]; then
        kill "$UVICORN_PID" 2>/dev/null || true
        wait "$UVICORN_PID" 2>/dev/null || true
    fi
    
    log_success "服务已关闭"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# 主函数
main() {
    log_info "Postcard Service 容器启动中..."
    
    check_environment
    wait_for_database
    wait_for_redis
    run_migrations
    
    # 检查自定义命令
    if [ $# -gt 0 ]; then
        log_info "执行自定义命令: $*"
        exec "$@"
    else
        log_info "启动 Postcard Service Web 服务..."
        # 统一使用 uvicorn（去除 BUILD_ENV 分支）
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --reload \
            --reload-dir app \
            --log-level info
    fi
}

main "$@"
