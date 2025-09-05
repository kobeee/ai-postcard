#!/bin/bash

# =============================================================================
# AI 明信片项目 - 部署系统验证脚本
# =============================================================================
# 功能：验证整个部署系统的正确性，包括脚本、配置文件和命令
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 计数器
TESTS_PASSED=0
TESTS_FAILED=0

# 日志函数
log_info() {
    printf "${BLUE}[INFO]${NC} %s\n" "$1"
}

log_success() {
    printf "${GREEN}[✅ PASS]${NC} %s\n" "$1"
    ((TESTS_PASSED++))
}

log_error() {
    printf "${RED}[❌ FAIL]${NC} %s\n" "$1"
    ((TESTS_FAILED++))
}

log_warning() {
    printf "${YELLOW}[⚠️  WARN]${NC} %s\n" "$1"
}

log_step() {
    printf "${PURPLE}[STEP]${NC} %s\n" "$1"
}

# 测试函数
test_file_exists() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        log_success "$description: $file 存在"
        return 0
    else
        log_error "$description: $file 不存在"
        return 1
    fi
}

test_script_syntax() {
    local script="$1"
    local description="$2"
    
    if bash -n "$script" 2>/dev/null; then
        log_success "$description: 语法正确"
        return 0
    else
        log_error "$description: 语法错误"
        return 1
    fi
}

test_docker_compose_config() {
    local compose_file="$1"
    local description="$2"
    
    if docker-compose -f "$compose_file" config --quiet 2>/dev/null; then
        log_success "$description: 配置文件正确"
        return 0
    else
        log_error "$description: 配置文件有误"
        return 1
    fi
}

# 主验证函数
main_validation() {
    log_step "开始验证 AI 明信片项目部署系统..."
    
    # 1. 验证核心配置文件
    log_info "1. 验证配置文件..."
    test_file_exists ".env" "环境变量配置"
    test_file_exists "docker-compose.yml" "开发环境Docker Compose"
    test_file_exists "docker-compose.prod.yml" "生产环境Docker Compose"
    test_docker_compose_config "docker-compose.yml" "开发环境配置"
    test_docker_compose_config "docker-compose.prod.yml" "生产环境配置"
    
    # 2. 验证脚本文件
    log_info "2. 验证管理脚本..."
    test_file_exists "scripts/init-project.sh" "项目初始化脚本"
    test_file_exists "scripts/init-redis.sh" "Redis初始化脚本" 
    test_file_exists "scripts/init-database.sql" "数据库初始化脚本"
    test_file_exists "scripts/dev.sh" "开发环境管理脚本"
    test_file_exists "scripts/prod.sh" "生产环境管理脚本"
    
    test_script_syntax "scripts/init-project.sh" "项目初始化脚本"
    test_script_syntax "scripts/init-redis.sh" "Redis初始化脚本"
    test_script_syntax "scripts/dev.sh" "开发环境管理脚本"
    test_script_syntax "scripts/prod.sh" "生产环境管理脚本"
    
    # 3. 验证Dockerfile文件
    log_info "3. 验证Docker镜像文件..."
    local services=("gateway-service" "user-service" "postcard-service" "ai-agent-service")
    for service in "${services[@]}"; do
        local dockerfile="src/$service/Dockerfile"
        test_file_exists "$dockerfile" "$service Dockerfile"
        
        # 检查Dockerfile基本结构
        if [ -f "$dockerfile" ]; then
            if grep -q "FROM" "$dockerfile" && grep -q "WORKDIR" "$dockerfile"; then
                log_success "$service Dockerfile: 基本结构正确"
            else
                log_error "$service Dockerfile: 基本结构缺失"
            fi
        fi
    done
    
    # 4. 验证配置目录结构
    log_info "4. 验证配置目录结构..."
    local required_dirs=(
        "configs/nginx"
        "src/gateway-service"
        "src/user-service" 
        "src/postcard-service"
        "src/ai-agent-service"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_success "目录结构: $dir 存在"
        else
            log_error "目录结构: $dir 不存在"
        fi
    done
    
    # 5. 验证Nginx配置
    log_info "5. 验证Nginx配置..."
    test_file_exists "configs/nginx/nginx.conf" "Nginx主配置文件"
    if [ -f "configs/nginx/nginx.conf" ]; then
        if grep -q "upstream" "configs/nginx/nginx.conf"; then
            log_success "Nginx配置: 包含upstream定义"
        else
            log_error "Nginx配置: 缺少upstream定义"
        fi
    fi
    
    # 6. 验证环境变量
    log_info "6. 验证关键环境变量..."
    source .env 2>/dev/null || {
        log_error "环境变量: .env文件无法加载"
        return 1
    }
    
    local required_vars=("DB_PASSWORD" "REDIS_PASSWORD" "APP_SECRET" "ANTHROPIC_AUTH_TOKEN")
    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            log_success "环境变量: $var 已设置"
        else
            log_error "环境变量: $var 未设置"
        fi
    done
    
    # 7. 验证Docker Compose服务定义
    log_info "7. 验证Docker Compose服务..."
    
    # 基础服务
    if docker-compose -f docker-compose.prod.yml config --services 2>/dev/null | grep -q "postgres"; then
        log_success "服务定义: PostgreSQL 数据库"
    else
        log_error "服务定义: PostgreSQL 数据库缺失"
    fi
    
    if docker-compose -f docker-compose.prod.yml config --services 2>/dev/null | grep -q "redis"; then
        log_success "服务定义: Redis 缓存"
    else
        log_error "服务定义: Redis 缓存缺失"
    fi
    
    # 应用服务
    if docker-compose -f docker-compose.prod.yml --profile all config --services 2>/dev/null | grep -q "ai-agent-service"; then
        log_success "服务定义: AI Agent 服务"
    else
        log_error "服务定义: AI Agent 服务缺失"
    fi
    
    # 8. 验证关键命令
    log_info "8. 验证关键命令..."
    
    # 验证help命令
    if sh scripts/prod.sh help >/dev/null 2>&1; then
        log_success "命令验证: prod.sh help 正常"
    else
        log_error "命令验证: prod.sh help 失败"
    fi
    
    # 验证配置验证命令
    if docker-compose -f docker-compose.prod.yml --profile all config --quiet >/dev/null 2>&1; then
        log_success "命令验证: docker-compose 配置验证正常"
    else
        log_error "命令验证: docker-compose 配置验证失败"
    fi
    
    # 9. 输出最终结果
    log_step "验证完成！"
    echo ""
    log_info "验证结果统计："
    printf "  ${GREEN}通过测试: %d${NC}\n" "$TESTS_PASSED"
    printf "  ${RED}失败测试: %d${NC}\n" "$TESTS_FAILED"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "🎉 所有测试通过！部署系统验证成功！"
        echo ""
        echo "✅ 你现在可以安全地使用以下命令："
        echo "   docker-compose -f docker-compose.prod.yml --profile all build --no-cache"
        echo "   sh scripts/prod.sh up all"
        return 0
    else
        log_error "❌ 发现 $TESTS_FAILED 个问题，请修复后重新验证"
        return 1
    fi
}

# 执行验证
main_validation "$@"