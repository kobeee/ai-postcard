#!/bin/bash

# =============================================================================
# Gateway Service - Docker 容器启动脚本
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
    
    local required_vars=("APP_SECRET")
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

# 等待后端服务
wait_for_backend_services() {
    log_info "检查后端服务连接..."
    
    # 检查用户服务
    if [ -n "${USER_SERVICE_URL:-}" ]; then
        local max_attempts=10
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f "${USER_SERVICE_URL}/health" >/dev/null 2>&1; then
                log_success "用户服务连接成功"
                break
            fi
            
            log_info "等待用户服务 ($attempt/$max_attempts)..."
            sleep 3
            attempt=$((attempt + 1))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_warning "用户服务连接超时，但继续启动"
        fi
    fi
    
    # 检查其他后端服务的连接性...
    log_success "后端服务检查完成"
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
    log_info "Gateway Service 容器启动中..."
    log_info "环境: ${BUILD_ENV:-development}"
    
    check_environment
    wait_for_backend_services
    
    # 检查自定义命令
    if [ $# -gt 0 ]; then
        log_info "执行自定义命令: $*"
        exec "$@"
    else
        log_info "启动 Gateway Service Web 服务..."
        
        if [ "${BUILD_ENV}" = "production" ]; then
            exec gunicorn app.main:app \
                --workers 4 \
                --worker-class uvicorn.workers.UvicornWorker \
                --bind 0.0.0.0:8000 \
                --access-logfile - \
                --log-level info
        else
            exec uvicorn app.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --reload \
                --log-level debug
        fi
    fi
}

main "$@"