#!/bin/bash

# =============================================================================
# AI 明信片项目 - 开发环境统一管理脚本
# =============================================================================
# 用法：
#   sh scripts/dev.sh up <profile1> <profile2> ...    # 启动服务
#   sh scripts/dev.sh down                            # 停止所有服务
#   sh scripts/dev.sh logs <service_name>             # 查看服务日志
#   sh scripts/dev.sh restart <service_name>          # 重启服务
#   sh scripts/dev.sh ps                              # 查看服务状态
#   sh scripts/dev.sh exec <service_name> <command>   # 在服务容器中执行命令
#   sh scripts/dev.sh validate-env                    # 验证环境配置
#   sh scripts/dev.sh clean                           # 清理容器和卷
#   sh scripts/dev.sh help                            # 显示帮助信息

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 和 Docker Compose 是否安装
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装或不在 PATH 中"
        exit 1
    fi
}

# 检查 .env 文件是否存在
check_env_file() {
    if [ ! -f .env ]; then
        log_warning ".env 文件不存在"
        log_info "正在从 .env.example 创建 .env 文件..."
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success ".env 文件已创建，请根据需要修改配置"
        else
            log_error ".env.example 文件不存在，无法创建 .env"
            exit 1
        fi
    fi
}

# 验证环境变量
validate_env() {
    log_info "验证环境变量..."
    
    # 加载 .env 文件
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    fi
    
    # 必需的环境变量
    required_vars=(
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "APP_SECRET"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "缺少必需的环境变量："
        printf "   %s\n" "${missing_vars[@]}"
        echo ""
        log_error "请检查 .env 文件并设置这些变量"
        exit 1
    else
        log_success "所有必需的环境变量已设置"
    fi
}

# 检查是否需要重建
check_need_rebuild() {
    local need_rebuild=false
    
    # 如果设置了强制重建环境变量，优先处理
    if [ "${FORCE_REBUILD:-false}" = "true" ]; then
        need_rebuild=true
        log_info "检测到 FORCE_REBUILD=true，强制重建" >&2
        echo $need_rebuild
        return
    fi
    
    # 检查关键文件是否有变化
    local key_files=(
        "docker-compose.yml"
        "src/ai-agent-service/Dockerfile.dev"
        "src/ai-agent-service/requirements.txt"
        "src/gateway-service/Dockerfile.dev"
        "src/gateway-service/package.json"
        "src/user-service/Dockerfile.dev"
        "src/user-service/requirements.txt"
        "src/postcard-service/Dockerfile.dev"
        "src/postcard-service/requirements.txt"
    )
    
    # 检查镜像是否存在
    for profile in "$@"; do
        case $profile in
            "agent"|"agent-tests"|"agent-script")
                if ! docker images -q ai-postcard-ai-agent-service &> /dev/null; then
                    need_rebuild=true
                    log_info "AI Agent 服务镜像不存在，需要构建"
                    break
                fi
                ;;
            "gateway")
                if ! docker images -q ai-postcard-gateway-service &> /dev/null; then
                    need_rebuild=true
                    log_info "Gateway 服务镜像不存在，需要构建"
                    break
                fi
                ;;
            "user"|"user-tests")
                if ! docker images -q ai-postcard-user-service &> /dev/null; then
                    need_rebuild=true
                    log_info "User 服务镜像不存在，需要构建"
                    break
                fi
                ;;
            "postcard"|"postcard-tests")
                if ! docker images -q ai-postcard-postcard-service &> /dev/null; then
                    need_rebuild=true
                    log_info "Postcard 服务镜像不存在，需要构建"
                    break
                fi
                ;;
        esac
    done
    

    
    echo $need_rebuild
}

# 启动服务
start_services() {
    if [ $# -eq 0 ]; then
        log_error "请指定要启动的服务 profile"
        echo "可用的 profiles："
        echo "  gateway        - API 网关服务"
        echo "  user           - 用户服务"
        echo "  user-tests     - 用户服务测试"
        echo "  postcard       - 明信片服务"
        echo "  postcard-tests - 明信片服务测试"
        echo "  agent          - AI Agent 服务"
        echo "  agent-tests    - AI Agent 测试"
        echo "  agent-script   - AI Agent 脚本执行"
        echo ""
        echo "示例："
        echo "  sh scripts/dev.sh up gateway user    # 启动网关和用户服务"
        echo "  sh scripts/dev.sh up agent-tests     # 运行 AI Agent 测试"
        echo "  FORCE_REBUILD=true sh scripts/dev.sh up agent  # 强制重建"
        exit 1
    fi
    
    profiles="$*"
    log_info "启动服务 profiles: $profiles"
    
    # 检查是否需要重建
    need_rebuild=$(check_need_rebuild "$@")
    
    if [ "$need_rebuild" = "true" ]; then
        log_info "检测到需要重建，正在构建镜像..."
        docker-compose $(echo $profiles | sed 's/[^ ]* */--profile &/g') up --build -d
    else
        log_info "使用现有镜像启动服务..."
        docker-compose $(echo $profiles | sed 's/[^ ]* */--profile &/g') up -d
    fi
    
    log_success "服务启动完成"
    
    # 显示服务状态
    echo ""
    docker-compose ps
}

# 停止服务
stop_services() {
    log_info "停止所有服务..."
    
    # 首先尝试停止所有可能的 profiles
    docker-compose --profile gateway --profile user --profile postcard --profile agent down 2>/dev/null || true
    
    # 然后执行标准的 down 命令
    docker-compose down
    
    # 强制停止任何剩余的项目相关容器
    docker ps --format "table {{.Names}}\t{{.Image}}" | grep "ai-postcard" | cut -f1 | xargs -r docker stop 2>/dev/null || true
    
    log_success "所有服务已停止"
}

# 查看日志
show_logs() {
    if [ $# -eq 0 ]; then
        log_info "显示所有服务日志..."
        docker-compose logs -f
    else
        service_name=$1
        log_info "显示服务 $service_name 的日志..."
        docker-compose logs -f "$service_name"
    fi
}

# 重启服务
restart_service() {
    if [ $# -eq 0 ]; then
        log_error "请指定要重启的服务名称"
        exit 1
    fi
    
    service_name=$1
    log_info "重启服务: $service_name"
    
    docker-compose restart "$service_name"
    log_success "服务 $service_name 已重启"
}

# 查看服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
}

# 在容器中执行命令
exec_command() {
    if [ $# -lt 2 ]; then
        log_error "用法: sh scripts/dev.sh exec <service_name> <command>"
        exit 1
    fi
    
    service_name=$1
    shift
    command="$*"
    
    log_info "在服务 $service_name 中执行: $command"
    docker-compose exec "$service_name" $command
}

# 清理容器和卷
clean_all() {
    log_warning "这将删除所有容器、网络和卷，数据将丢失！"
    read -p "确定要继续吗？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理容器和卷..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        log_success "清理完成"
    else
        log_info "取消清理操作"
    fi
}

# 显示帮助信息
show_help() {
    echo "AI 明信片项目开发环境管理脚本"
    echo ""
    echo "用法："
    echo "  sh scripts/dev.sh <command> [options]"
    echo ""
    echo "命令："
    echo "  up <profile...>              启动指定的服务 profiles"
    echo "  down                         停止所有服务"
    echo "  logs [service_name]          查看服务日志"
    echo "  restart <service_name>       重启指定服务"
    echo "  ps                           查看服务状态"
    echo "  exec <service> <command>     在服务容器中执行命令"
    echo "  validate-env                 验证环境配置"
    echo "  clean                        清理所有容器和卷"
    echo "  help                         显示此帮助信息"
    echo ""
    echo "可用的服务 profiles："
    echo "  gateway        - API 网关服务"
    echo "  user           - 用户服务"
    echo "  user-tests     - 用户服务测试"
    echo "  postcard       - 明信片服务"
    echo "  postcard-tests - 明信片服务测试"
    echo "  agent          - AI Agent 服务"
    echo "  agent-tests    - AI Agent 测试"
    echo "  agent-script   - AI Agent 脚本执行"
    echo ""
    echo "示例："
    echo "  sh scripts/dev.sh up gateway user           # 启动网关和用户服务"
    echo "  sh scripts/dev.sh up agent                  # 启动 AI Agent 服务"
    echo "  sh scripts/dev.sh logs gateway-service      # 查看网关服务日志"
    echo "  sh scripts/dev.sh exec ai-agent-service bash # 进入 AI Agent 容器"
    echo "  SCRIPT_COMMAND='python manage.py migrate' sh scripts/dev.sh up agent-script"
}

# 主函数
main() {
    # 检查依赖
    check_dependencies
    
    # 检查环境文件
    check_env_file
    
    # 解析命令
    case "${1:-help}" in
        "up")
            shift
            start_services "$@"
            ;;
        "down")
            stop_services
            ;;
        "logs")
            shift
            show_logs "$@"
            ;;
        "restart")
            shift
            restart_service "$@"
            ;;
        "ps")
            show_status
            ;;
        "exec")
            shift
            exec_command "$@"
            ;;
        "validate-env")
            validate_env
            ;;
        "clean")
            clean_all
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
