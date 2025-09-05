#!/bin/bash

# =============================================================================
# AI 明信片项目 - 生产环境管理脚本
# =============================================================================
# 用法：
#   sh scripts/prod.sh init                               # 初始化生产环境
#   sh scripts/prod.sh up <profile1> <profile2> ...       # 启动服务
#   sh scripts/prod.sh down                               # 停止所有服务
#   sh scripts/prod.sh restart <service_name>             # 重启服务
#   sh scripts/prod.sh logs <service_name>                # 查看服务日志
#   sh scripts/prod.sh ps                                 # 查看服务状态
#   sh scripts/prod.sh exec <service_name> <command>      # 在容器中执行命令
#   sh scripts/prod.sh backup                             # 数据备份
#   sh scripts/prod.sh restore <backup_file>              # 数据恢复
#   sh scripts/prod.sh health                             # 健康检查
#   sh scripts/prod.sh scale <service_name> <replicas>    # 扩容服务
#   sh scripts/prod.sh cleanup                            # 清理系统资源
#   sh scripts/prod.sh help                               # 显示帮助信息
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 生产环境配置
PROD_COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="./backups"
LOG_RETENTION_DAYS=30

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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 检查依赖
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装或不在 PATH 中"
        exit 1
    fi

    # 检查生产环境配置文件
    if [ ! -f "$PROD_COMPOSE_FILE" ]; then
        log_error "生产环境配置文件 $PROD_COMPOSE_FILE 不存在"
        exit 1
    fi
}

# 检查环境变量
check_env_file() {
    if [ ! -f .env ]; then
        log_error ".env 文件不存在"
        log_error "请先运行: sh scripts/init-project.sh --env=prod"
        exit 1
    fi
    
    # 验证关键环境变量
    source .env 2>/dev/null || {
        log_error ".env 文件格式错误"
        exit 1
    }
    
    local required_vars=(
        "DB_PASSWORD"
        "REDIS_PASSWORD" 
        "APP_SECRET"
        "ANTHROPIC_AUTH_TOKEN"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "生产环境缺少必需的环境变量："
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
}

# 创建必要的目录
ensure_directories() {
    local dirs=(
        "$BACKUP_DIR"
        "./data/postgres"
        "./data/redis"
        "./data/ai-agent/static"
        "./logs/postgres"
        "./logs/redis" 
        "./logs/nginx"
        "./logs/gateway"
        "./logs/user"
        "./logs/postcard"
        "./logs/ai-agent"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        # 设置适当的权限
        if [[ "$dir" == "./data/"* ]]; then
            chmod 755 "$dir"
        elif [[ "$dir" == "./logs/"* ]]; then
            chmod 755 "$dir"
        fi
    done
}

# 初始化生产环境
init_production() {
    log_step "初始化生产环境..."
    
    # 运行项目初始化脚本
    if [ -f "scripts/init-project.sh" ]; then
        sh scripts/init-project.sh --env=prod
    else
        log_error "项目初始化脚本不存在"
        exit 1
    fi
    
    log_success "生产环境初始化完成"
}

# 启动服务
start_services() {
    local profiles=("$@")
    
    if [ ${#profiles[@]} -eq 0 ]; then
        log_error "请指定要启动的服务配置文件"
        log_info "可用配置: all, gateway, user, postcard, agent, worker, nginx"
        exit 1
    fi
    
    log_step "启动生产环境服务: ${profiles[*]}"
    
    ensure_directories
    
    # 使用生产环境配置启动服务
    for profile in "${profiles[@]}"; do
        log_info "启动 $profile 服务..."
        docker-compose -f "$PROD_COMPOSE_FILE" --profile "$profile" up -d
    done
    
    # 等待服务启动
    log_info "等待服务启动完成..."
    sleep 10
    
    # 检查服务状态
    show_status
    
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_step "停止所有生产环境服务..."
    
    docker-compose -f "$PROD_COMPOSE_FILE" down
    
    log_success "服务已停止"
}

# 重启服务
restart_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        log_error "请指定要重启的服务名称"
        exit 1
    fi
    
    log_step "重启服务: $service_name"
    
    docker-compose -f "$PROD_COMPOSE_FILE" restart "$service_name"
    
    log_success "服务 $service_name 已重启"
}

# 查看日志
show_logs() {
    local service_name="$1"
    local follow_flag=""
    
    if [ "$2" = "-f" ] || [ "$2" = "--follow" ]; then
        follow_flag="-f"
    fi
    
    if [ -z "$service_name" ]; then
        log_info "显示所有服务日志"
        docker-compose -f "$PROD_COMPOSE_FILE" logs $follow_flag --tail=100
    else
        log_info "显示服务日志: $service_name"
        docker-compose -f "$PROD_COMPOSE_FILE" logs $follow_flag --tail=100 "$service_name"
    fi
}

# 查看服务状态
show_status() {
    log_info "生产环境服务状态："
    docker-compose -f "$PROD_COMPOSE_FILE" ps
    
    echo ""
    log_info "Docker系统资源使用："
    docker system df
    
    echo ""
    log_info "容器资源使用："
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 在容器中执行命令
exec_command() {
    local service_name="$1"
    shift
    local command=("$@")
    
    if [ -z "$service_name" ]; then
        log_error "请指定服务名称"
        exit 1
    fi
    
    if [ ${#command[@]} -eq 0 ]; then
        command=("bash")
    fi
    
    log_info "在 $service_name 中执行命令: ${command[*]}"
    
    docker-compose -f "$PROD_COMPOSE_FILE" exec "$service_name" "${command[@]}"
}

# 数据备份
backup_data() {
    log_step "开始数据备份..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/backup_$timestamp.tar.gz"
    
    ensure_directories
    
    # 创建数据库备份
    log_info "备份PostgreSQL数据库..."
    docker-compose -f "$PROD_COMPOSE_FILE" exec -T postgres pg_dumpall -U postgres > "$BACKUP_DIR/postgres_$timestamp.sql"
    
    # 备份Redis数据
    log_info "备份Redis数据..."
    docker-compose -f "$PROD_COMPOSE_FILE" exec -T redis redis-cli -a "$REDIS_PASSWORD" --rdb /tmp/dump.rdb
    docker cp "$(docker-compose -f "$PROD_COMPOSE_FILE" ps -q redis):/tmp/dump.rdb" "$BACKUP_DIR/redis_$timestamp.rdb"
    
    # 备份应用数据和配置
    log_info "备份应用数据..."
    tar -czf "$backup_file" \
        --exclude="./logs" \
        --exclude="./backups/*.tar.gz" \
        ./data \
        ./.env \
        "$BACKUP_DIR/postgres_$timestamp.sql" \
        "$BACKUP_DIR/redis_$timestamp.rdb"
    
    # 清理临时文件
    rm -f "$BACKUP_DIR/postgres_$timestamp.sql" "$BACKUP_DIR/redis_$timestamp.rdb"
    
    log_success "备份完成: $backup_file"
    
    # 清理旧备份（保留最近7天）
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
}

# 数据恢复
restore_data() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_error "请提供有效的备份文件路径"
        exit 1
    fi
    
    log_warning "数据恢复将覆盖现有数据，请确认操作！"
    read -p "继续恢复？(y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "已取消恢复操作"
        exit 0
    fi
    
    log_step "开始数据恢复..."
    
    # 停止服务
    stop_services
    
    # 解压备份文件
    tar -xzf "$backup_file" -C /
    
    # 启动服务
    start_services all
    
    log_success "数据恢复完成"
}

# 健康检查
health_check() {
    log_step "执行系统健康检查..."
    
    local unhealthy_services=()
    
    # 检查各个服务的健康状态
    local services=("gateway-service" "user-service" "postcard-service" "ai-agent-service")
    
    for service in "${services[@]}"; do
        local container_name="ai-postcard-${service%-service}-prod"
        
        if docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
            log_success "$service: 健康"
        else
            log_warning "$service: 不健康或未启动"
            unhealthy_services+=("$service")
        fi
    done
    
    # 检查数据库连接
    if docker-compose -f "$PROD_COMPOSE_FILE" exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        log_success "PostgreSQL: 连接正常"
    else
        log_warning "PostgreSQL: 连接异常"
        unhealthy_services+=("postgres")
    fi
    
    # 检查Redis连接  
    if docker-compose -f "$PROD_COMPOSE_FILE" exec -T redis redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        log_success "Redis: 连接正常"
    else
        log_warning "Redis: 连接异常"
        unhealthy_services+=("redis")
    fi
    
    # 检查磁盘空间
    local disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        log_success "磁盘空间: ${disk_usage}% 使用正常"
    else
        log_warning "磁盘空间: ${disk_usage}% 使用率过高"
    fi
    
    # 输出结果
    if [ ${#unhealthy_services[@]} -eq 0 ]; then
        log_success "所有服务健康状态正常"
    else
        log_warning "以下服务需要关注: ${unhealthy_services[*]}"
        return 1
    fi
}

# 扩容服务
scale_service() {
    local service_name="$1"
    local replicas="$2"
    
    if [ -z "$service_name" ] || [ -z "$replicas" ]; then
        log_error "用法: scale <service_name> <replicas>"
        exit 1
    fi
    
    if ! [[ "$replicas" =~ ^[0-9]+$ ]]; then
        log_error "副本数必须是数字"
        exit 1
    fi
    
    log_step "扩容服务 $service_name 到 $replicas 个副本"
    
    docker-compose -f "$PROD_COMPOSE_FILE" up -d --scale "$service_name=$replicas" "$service_name"
    
    log_success "服务扩容完成"
    show_status
}

# 清理系统资源
cleanup_system() {
    log_step "清理系统资源..."
    
    # 清理停止的容器
    log_info "清理停止的容器..."
    docker container prune -f
    
    # 清理未使用的镜像
    log_info "清理未使用的镜像..."
    docker image prune -f
    
    # 清理未使用的网络
    log_info "清理未使用的网络..."
    docker network prune -f
    
    # 清理未使用的卷
    log_warning "清理未使用的数据卷..."
    docker volume prune -f
    
    # 清理旧日志文件
    log_info "清理旧日志文件..."
    find ./logs -name "*.log" -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
    
    # 显示清理结果
    log_success "系统资源清理完成"
    docker system df
}

# 显示帮助信息
show_help() {
    echo "AI 明信片项目 - 生产环境管理脚本"
    echo ""
    echo "用法:"
    echo "  $0 init                                    初始化生产环境"
    echo "  $0 up <profile1> [profile2] ...           启动服务"
    echo "  $0 down                                    停止所有服务"
    echo "  $0 restart <service_name>                  重启指定服务"
    echo "  $0 logs <service_name> [-f]               查看服务日志"
    echo "  $0 ps                                      查看服务状态"
    echo "  $0 exec <service_name> [command]          在容器中执行命令"
    echo "  $0 backup                                  备份数据"
    echo "  $0 restore <backup_file>                   恢复数据"
    echo "  $0 health                                  健康检查"
    echo "  $0 scale <service_name> <replicas>         扩容服务"
    echo "  $0 cleanup                                 清理系统资源"
    echo "  $0 help                                    显示此帮助信息"
    echo ""
    echo "可用的服务配置 (profiles):"
    echo "  all        - 所有服务"
    echo "  gateway    - API网关"
    echo "  user       - 用户服务"
    echo "  postcard   - 明信片服务"
    echo "  agent      - AI Agent服务"
    echo "  worker     - AI Agent工作进程"
    echo "  nginx      - Nginx反向代理"
    echo ""
    echo "服务名称:"
    echo "  gateway-service, user-service, postcard-service"
    echo "  ai-agent-service, ai-agent-worker, postgres, redis, nginx"
    echo ""
}

# 主函数
main() {
    local command="$1"
    shift || true
    
    case "$command" in
        init)
            check_dependencies
            init_production
            ;;
        up)
            check_dependencies
            check_env_file
            start_services "$@"
            ;;
        down)
            check_dependencies
            stop_services
            ;;
        restart)
            check_dependencies
            restart_service "$@"
            ;;
        logs)
            check_dependencies
            show_logs "$@"
            ;;
        ps)
            check_dependencies
            show_status
            ;;
        exec)
            check_dependencies
            exec_command "$@"
            ;;
        backup)
            check_dependencies
            check_env_file
            backup_data
            ;;
        restore)
            check_dependencies
            check_env_file
            restore_data "$@"
            ;;
        health)
            check_dependencies
            check_env_file
            health_check
            ;;
        scale)
            check_dependencies
            scale_service "$@"
            ;;
        cleanup)
            check_dependencies
            cleanup_system
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"