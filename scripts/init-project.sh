#!/bin/bash

# =============================================================================
# AI 明信片项目 - 项目初始化脚本
# =============================================================================
# 功能：初始化整个项目的生产和开发环境
# 用法：sh scripts/init-project.sh [--env=dev|prod] [--force]
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

# 默认参数
ENVIRONMENT="dev"
FORCE_INIT=false

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --env=*)
            ENVIRONMENT="${arg#*=}"
            shift
            ;;
        --force)
            FORCE_INIT=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [--env=dev|prod] [--force]"
            echo "  --env=dev|prod    设置环境类型 (默认: dev)"
            echo "  --force           强制重新初始化"
            echo "  --help            显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $arg"
            echo "使用 --help 查看用法"
            exit 1
            ;;
    esac
done

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
    log_step "检查系统依赖..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少依赖: ${missing_deps[*]}"
        log_error "请安装后重试"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 环境配置检查和创建
setup_environment() {
    log_step "配置环境变量..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_info "从 .env.example 创建 .env 文件"
            cp .env.example .env
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    elif [ "$FORCE_INIT" = true ]; then
        log_warning "强制模式：重新创建 .env 文件"
        cp .env.example .env
    fi
    
    # 验证关键环境变量
    source .env 2>/dev/null || true
    
    local required_vars=("DB_PASSWORD" "REDIS_PASSWORD" "APP_SECRET")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_warning "以下环境变量未设置: ${missing_vars[*]}"
        log_info "请编辑 .env 文件设置这些变量后重新运行初始化"
        
        # 生成随机密码建议
        log_info "建议的配置值："
        for var in "${missing_vars[@]}"; do
            case $var in
                DB_PASSWORD|REDIS_PASSWORD|APP_SECRET)
                    echo "  $var=$(openssl rand -base64 32 | tr -d '/+=' | head -c 24)"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "环境变量配置完成"
}

# 创建必要的目录结构
create_directories() {
    log_step "创建项目目录结构..."
    
    local dirs=(
        "logs"
        "data/postgres"
        "data/redis"
        "uploads"
        "src/ai-agent-service/logs"
        "src/gateway-service/logs" 
        "src/user-service/logs"
        "src/postcard-service/logs"
        "src/ai-agent-service/app/static/generated"
        "src/ai-agent-service/app/static/assets"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
    
    # 设置适当的权限
    chmod -R 755 logs/ data/ uploads/ 2>/dev/null || true
    chmod -R 755 src/*/logs/ 2>/dev/null || true
    
    # 创建所有服务的挂载目录
    mkdir -p logs/nginx logs/gateway logs/user logs/postcard logs/ai-agent
    mkdir -p data/postgres data/redis data/ai-agent/static
    
    # 为各种容器设置正确的目录权限
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "设置容器挂载目录权限..."
        
        # 数据目录权限设置（使用Docker volumes，不需要特殊权限）
        log_info "  → 数据目录基础权限设置"
        chmod -R 755 data/postgres data/redis data/ai-agent 2>/dev/null || true
        
        # Nginx (nginx用户UID=101, GID=101)
        log_info "  → Nginx权限设置 (UID=101)"
        chown -R 101:101 logs/nginx 2>/dev/null || true
        chmod -R 755 logs/nginx 2>/dev/null || true
        
        # Python服务 (appuser用户UID=1000, GID=1000)
        log_info "  → Python服务权限设置 (UID=1000)"
        for service_dir in logs/gateway logs/user logs/postcard logs/ai-agent data/ai-agent; do
            chown -R 1000:1000 "$service_dir" 2>/dev/null || true
            chmod -R 755 "$service_dir" 2>/dev/null || true
        done
        
        # 使用 setfacl 设置 ACL 权限（如果系统支持）
        if command -v setfacl &> /dev/null; then
            log_info "  → 使用ACL设置扩展权限"
            setfacl -m u:101:rwx -R logs/nginx 2>/dev/null || true
            setfacl -m u:1000:rwx -R logs/gateway logs/user logs/postcard logs/ai-agent data/ai-agent 2>/dev/null || true
        fi
        
        log_success "容器挂载目录权限设置完成"
        log_info "注意: PostgreSQL 和 Redis 使用容器内部日志，可通过 'docker logs' 命令查看"
    fi
    
    log_success "目录结构创建完成"
}

# 初始化数据库
init_database() {
    log_step "初始化数据库..."
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "使用生产环境配置启动数据库"
        docker-compose -f docker-compose.prod.yml up -d postgres redis
    else
        log_info "使用开发环境配置启动数据库"
        docker-compose up -d postgres redis
    fi
    
    # 等待数据库和Redis启动
    log_info "等待数据库服务启动..."
    sleep 10
    
    # 设置容器名称后缀
    local suffix=""
    if [ "$ENVIRONMENT" = "prod" ]; then
        suffix="-prod"
    fi
    
    # 检查数据库连接
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec ai-postcard-postgres${suffix} pg_isready -U postgres >/dev/null 2>&1; then
            log_success "PostgreSQL 连接成功"
            break
        fi
        
        log_info "等待 PostgreSQL 启动... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "PostgreSQL 启动超时"
        exit 1
    fi
    
    # 检查Redis连接
    if docker exec ai-postcard-redis${suffix} redis-cli -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1; then
        log_success "Redis 连接成功"
    else
        log_warning "Redis 连接失败，但将继续初始化"
    fi
    
    # 执行数据库初始化脚本
    log_info "执行数据库表结构初始化..."
    docker exec -i ai-postcard-postgres psql -U postgres -d ai_postcard < scripts/init-database.sql || {
        log_warning "数据库初始化脚本执行出现警告，但继续进行"
    }
    
    log_success "数据库初始化完成"
}

# 初始化Redis
init_redis() {
    log_step "初始化Redis队列和缓存结构..."
    
    # 创建Redis Stream和Consumer Group
    docker exec ai-postcard-redis redis-cli -a "${REDIS_PASSWORD}" XGROUP CREATE postcard_tasks ai_agent_workers 0 MKSTREAM >/dev/null 2>&1 || {
        log_info "Redis队列已存在或创建失败，跳过"
    }
    
    # 清理可能存在的旧缓存数据
    if [ "$FORCE_INIT" = true ]; then
        log_info "强制模式：清理Redis缓存数据"
        docker exec ai-postcard-redis redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "cache:*" | xargs docker exec -i ai-postcard-redis redis-cli -a "${REDIS_PASSWORD}" DEL >/dev/null 2>&1 || true
        docker exec ai-postcard-redis redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | xargs docker exec -i ai-postcard-redis redis-cli -a "${REDIS_PASSWORD}" DEL >/dev/null 2>&1 || true
    fi
    
    log_success "Redis 初始化完成"
}

# 构建服务镜像
build_services() {
    log_step "构建服务镜像..."
    
    local services=("ai-agent-service" "gateway-service" "user-service" "postcard-service")
    
    for service in "${services[@]}"; do
        log_info "构建 $service 镜像..."
        
        if [ "$ENVIRONMENT" = "prod" ]; then
            docker-compose -f docker-compose.prod.yml build "$service" --no-cache
        else
            docker-compose build "$service" --no-cache
        fi
        
        log_success "$service 镜像构建完成"
    done
}

# 验证初始化结果
verify_initialization() {
    log_step "验证初始化结果..."
    
    # 检查Docker网络
    if docker network ls | grep -q ai-postcard; then
        log_success "Docker网络创建成功"
    else
        log_warning "Docker网络未找到"
    fi
    
    # 检查数据卷
    if docker volume ls | grep -q postgres_data && docker volume ls | grep -q redis_data; then
        log_success "数据卷创建成功"
    else
        log_warning "部分数据卷未找到"
    fi
    
    # 检查服务镜像
    local services=("ai-agent-service" "gateway-service" "user-service" "postcard-service")
    for service in "${services[@]}"; do
        if docker images | grep -q "ai-postcard.*$service"; then
            log_success "$service 镜像存在"
        else
            log_warning "$service 镜像未找到"
        fi
    done
    
    log_success "初始化验证完成"
}

# 显示启动说明
show_usage_info() {
    log_step "项目启动说明"
    
    echo ""
    echo -e "${GREEN}项目初始化完成！${NC}"
    echo ""
    echo "后续操作："
    echo ""
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo "1. 启动生产环境："
        echo "   sh scripts/prod.sh up all"
        echo ""
        echo "2. 查看服务状态："
        echo "   sh scripts/prod.sh ps"
        echo ""
        echo "3. 查看日志："
        echo "   sh scripts/prod.sh logs [service-name]"
    else
        echo "1. 启动开发环境："
        echo "   sh scripts/dev.sh up all"
        echo ""
        echo "2. 启动特定服务："
        echo "   sh scripts/dev.sh up gateway user postcard agent"
        echo ""
        echo "3. 查看服务状态："
        echo "   sh scripts/dev.sh ps"
        echo ""
        echo "4. 查看日志："
        echo "   sh scripts/dev.sh logs [service-name]"
    fi
    
    echo ""
    echo "服务端口："
    echo "  - API网关:     http://localhost:8083"
    echo "  - AI Agent:    http://localhost:8080"
    echo "  - 用户服务:     http://localhost:8081"
    echo "  - 明信片服务:   http://localhost:8082"
    echo "  - PostgreSQL:  localhost:5432"
    echo "  - Redis:       localhost:6379"
    echo ""
    echo "配置文件："
    echo "  - 环境变量:    .env"
    echo "  - 数据库配置:  configs/postgres/"
    echo "  - 小程序配置:  src/miniprogram/config/"
    echo ""
}

# 主函数
main() {
    echo -e "${PURPLE}"
    echo "=============================================================================="
    echo "                         AI 明信片项目初始化"
    echo "=============================================================================="
    echo -e "${NC}"
    echo "环境类型: $ENVIRONMENT"
    echo "强制重初始化: $FORCE_INIT"
    echo ""
    
    check_dependencies
    setup_environment
    create_directories
    init_database
    init_redis
    build_services
    verify_initialization
    show_usage_info
    
    echo -e "${GREEN}"
    echo "=============================================================================="
    echo "                           初始化完成！"
    echo "=============================================================================="
    echo -e "${NC}"
}

# 运行主函数
main "$@"