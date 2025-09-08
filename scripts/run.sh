#!/bin/bash

# =============================================================================
# AI 明信片项目 - 统一部署脚本
# =============================================================================
# 简单高效的容器化部署，一个镜像到处跑
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查依赖
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
}

# 检查环境文件
check_env_file() {
    if [ ! -f .env ]; then
        log_warning ".env 文件不存在"
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success ".env 文件已创建"
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    fi
}

# 构建基础镜像
build_base() {
    log_info "构建基础镜像..."
    export DOCKER_BUILDKIT=1
    docker build -f docker/Dockerfile.base -t ai-postcard-base:latest .
    log_success "基础镜像构建完成"
}

# 检查基础镜像
check_base_image() {
    if ! docker images ai-postcard-base:latest --format "{{.Repository}}" | grep -q "ai-postcard-base"; then
        log_info "基础镜像不存在，开始构建..."
        build_base
    fi
}

# 确保目录和权限正确设置
ensure_directories_and_permissions() {
    log_info "创建必要目录和设置权限..."
    
    # 创建所有需要的目录
    mkdir -p logs/{gateway,user,postcard,ai-agent} \
             data/{postgres,redis,ai-agent/static} \
             backups/{postgres,redis}
    
    # 设置数据库和Redis数据目录权限
    # 注：在 macOS(Docker Desktop) 下不建议将宿主目录 chown 为 999:999，会导致容器无法创建子目录
    case "$(uname -s)" in
        Linux)
            if command -v chown &> /dev/null; then
                log_info "(Linux) 设置数据目录权限..."
                sudo chown -R 999:999 data/postgres data/redis 2>/dev/null || true
            fi
            ;;
        Darwin)
            log_info "(macOS) 跳过 chown 999:999，使用当前用户保持可写"
            ;;
        *)
            log_info "(其他平台) 保持默认权限"
            ;;
    esac
    
    # 设置应用日志和静态目录权限
    case "$(uname -s)" in
        Linux)
            chmod -R 755 logs/ data/ backups/ 2>/dev/null || true
            ;;
        Darwin)
            # macOS：放宽权限以避免 bind mount 写入问题
            log_info "(macOS) 放宽 logs/ 与 data/ai-agent/ 权限为 777"
            chmod -R 777 logs/ 2>/dev/null || true
            chmod -R 777 data/ai-agent/ 2>/dev/null || true
            # 其他目录保持默认
            ;;
        *)
            chmod -R 755 logs/ data/ backups/ 2>/dev/null || true
            ;;
    esac
    
    log_success "目录和权限设置完成"
}

# 仅清理用户数据（保留系统数据）
clean_user_data() {
    log_warning "即将清理数据库与缓存中的用户数据（保留系统数据），请确认已备份重要数据。"

    # 清理 PostgreSQL 用户数据
    log_info "清理 PostgreSQL 中的用户数据..."
    docker-compose exec -T postgres psql -U postgres -d ai_postcard -v ON_ERROR_STOP=1 -c "DO $$
DECLARE
    sys_user_uuid UUID;
    sys_user_str TEXT;
    deleted_users INTEGER := 0;
    deleted_quotas INTEGER := 0;  
    deleted_postcards INTEGER := 0;
    total_users_before INTEGER;
    total_quotas_before INTEGER;
    total_postcards_before INTEGER;
BEGIN
    -- 统计清理前的数据量
    SELECT COUNT(*) INTO total_users_before FROM users;
    SELECT COUNT(*) INTO total_quotas_before FROM user_quotas;
    SELECT COUNT(*) INTO total_postcards_before FROM postcards;
    
    RAISE NOTICE '=== 数据清理开始 ===';
    RAISE NOTICE '清理前统计 - 用户:%条, 配额:%条, 明信片:%条', total_users_before, total_quotas_before, total_postcards_before;
    
    -- 查找系统用户ID（UUID类型）
    SELECT id INTO sys_user_uuid
    FROM users
    WHERE openid = 'system_user' OR id = '00000000-0000-0000-0000-000000000000'::UUID
    LIMIT 1;
    
    -- 处理系统用户ID，转换为字符串用于VARCHAR字段比较
    IF sys_user_uuid IS NOT NULL THEN
        sys_user_str := sys_user_uuid::TEXT;
        RAISE NOTICE '找到系统用户 - UUID:%s, 字符串:%s', sys_user_uuid, sys_user_str;
    ELSE
        -- 创建系统用户（如果不存在）
        sys_user_uuid := '00000000-0000-0000-0000-000000000000'::UUID;
        sys_user_str := sys_user_uuid::TEXT;
        INSERT INTO users (id, openid, nickname, is_active) 
        VALUES (sys_user_uuid, 'system_user', '系统用户', true)
        ON CONFLICT (openid) DO NOTHING;
        RAISE NOTICE '创建系统用户 - UUID:%s, 字符串:%s', sys_user_uuid, sys_user_str;
    END IF;

    -- 1. 删除除系统用户外的所有用户（使用UUID类型比较）
    DELETE FROM users 
    WHERE id != sys_user_uuid;
    GET DIAGNOSTICS deleted_users = ROW_COUNT;
    RAISE NOTICE '✓ 删除普通用户记录: %条', deleted_users;

    -- 2. 删除所有非系统用户的配额记录（使用字符串类型比较，彻底清除每日限制）
    DELETE FROM user_quotas 
    WHERE user_id != sys_user_str;
    GET DIAGNOSTICS deleted_quotas = ROW_COUNT;
    RAISE NOTICE '✓ 删除用户配额记录: %条', deleted_quotas;

    -- 3. 删除所有非系统用户的明信片（使用字符串类型比较）
    DELETE FROM postcards 
    WHERE user_id != sys_user_str;
    GET DIAGNOSTICS deleted_postcards = ROW_COUNT;
    RAISE NOTICE '✓ 删除用户明信片记录: %条', deleted_postcards;
    
    -- 4. 清理孤立记录（没有user_id的记录）
    DELETE FROM user_quotas WHERE user_id IS NULL;
    DELETE FROM postcards WHERE user_id IS NULL;
    RAISE NOTICE '✓ 清理孤立记录完成';
    
    -- 最终统计
    DECLARE
        remaining_users INTEGER;
        remaining_quotas INTEGER;
        remaining_postcards INTEGER;
    BEGIN
        SELECT COUNT(*) INTO remaining_users FROM users;
        SELECT COUNT(*) INTO remaining_quotas FROM user_quotas;
        SELECT COUNT(*) INTO remaining_postcards FROM postcards;
        
        RAISE NOTICE '=== 数据清理完成 ===';
        RAISE NOTICE '清理后统计 - 用户:%条, 配额:%条, 明信片:%条', remaining_users, remaining_quotas, remaining_postcards;
        RAISE NOTICE '实际删除量 - 用户:%条, 配额:%条, 明信片:%条', deleted_users, deleted_quotas, deleted_postcards;
    END;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ 数据清理过程中发生错误: %', SQLERRM;
        RAISE;
END$$;" 2>&1
    log_success "PostgreSQL 用户数据清理完成"

    # 清理 Redis 用户数据（清理用户相关的缓存和会话）
    # 可用环境变量 CLEAN_REDIS_PATTERNS 自定义需清理的键（空格分隔通配模式）
    local patterns
    patterns=${CLEAN_REDIS_PATTERNS:-"postcard_tasks cache:user:* session:* temp:user:* quota:*"}

    log_info "清理 Redis 中的用户数据键: ${patterns}"
    
    # 逐个清理不同的键模式
    for pattern in ${patterns}; do
        log_info "清理模式: ${pattern}"
        # 获取匹配的键数量（用于日志显示）
        local key_count
        key_count=$(docker-compose exec -T redis sh -lc "redis-cli -a \"\${REDIS_PASSWORD:-redis}\" --no-auth-warning KEYS '${pattern}' | wc -l" 2>/dev/null || echo "0")
        
        if [ "${key_count}" -gt 0 ]; then
            log_info "找到 ${key_count} 个匹配的键"
            docker-compose exec -T redis sh -lc "redis-cli -a \"\${REDIS_PASSWORD:-redis}\" --no-auth-warning KEYS '${pattern}' | xargs -r redis-cli -a \"\${REDIS_PASSWORD:-redis}\" --no-auth-warning DEL" >/dev/null 2>&1 || true
        else
            log_info "未找到匹配的键"
        fi
    done

    # 业务所需流与消费者组：删除后需要恢复
    # 恢复 postcard_tasks 流与消费者组 ai_agent_workers（若已存在则忽略错误）
    docker-compose exec -T redis sh -lc "redis-cli -a \"\${REDIS_PASSWORD:-redis}\" --no-auth-warning XGROUP CREATE postcard_tasks ai_agent_workers 0 MKSTREAM" >/dev/null 2>&1 || true
    log_success "Redis 用户数据清理完成"
}

# 启动服务
up() {
    local profiles="$*"
    
    if [ -z "$profiles" ]; then
        log_error "请指定要启动的服务"
        show_profiles
        exit 1
    fi
    
    log_info "启动服务: $profiles"
    
    check_base_image
    ensure_directories_and_permissions
    
    # 构建profile参数
    local profile_args=""
    for profile in $profiles; do
        profile_args="$profile_args --profile $profile"
    done
    
    docker-compose $profile_args up -d --build
    
    log_success "服务启动完成"
    docker-compose ps
}

# 停止服务
down() {
    log_info "停止所有服务..."
    # 常规下线
    docker-compose down || true
    
    # 兜底：强制移除当前项目下仍在运行/存在的容器（避免遗留占用网络）
    local project_name
    project_name="$(basename "$PROJECT_ROOT")"
    containers=$(docker ps -a --filter "label=com.docker.compose.project=${project_name}" -q)
    if [ -n "$containers" ]; then
        log_warning "发现遗留容器，执行强制移除..."
        docker rm -f $containers >/dev/null 2>&1 || true
    fi

    # 清理遗留网络（如果仍被其他非本项目容器占用会失败，忽略即可）
    if docker network ls --format '{{.Name}}' | grep -q '^ai-postcard-network$'; then
        docker network rm ai-postcard-network >/dev/null 2>&1 || true
    fi

    log_success "服务已停止"
}

# 查看日志
logs() {
    local service="$1"
    local follow=""
    
    if [ "$2" = "-f" ]; then
        follow="-f"
    fi
    
    if [ -z "$service" ]; then
        docker-compose logs $follow --tail=100
    else
        docker-compose logs $follow --tail=100 "$service"
    fi
}

# 查看状态
ps() {
    docker-compose ps
}

# 在容器中执行命令
exec() {
    local service="$1"
    shift
    local cmd=("$@")
    
    if [ -z "$service" ]; then
        log_error "请指定服务名称"
        exit 1
    fi
    
    if [ ${#cmd[@]} -eq 0 ]; then
        cmd=("bash")
    fi
    
    docker-compose exec "$service" "${cmd[@]}"
}

# 重启服务
restart() {
    local service="$1"
    if [ -z "$service" ]; then
        log_error "请指定服务名称"
        exit 1
    fi
    
    docker-compose restart "$service"
    log_success "服务 $service 已重启"
}

# 初始化环境
init() {
    log_info "初始化环境..."
    
    ensure_directories_and_permissions
    
    # 启动数据库和缓存
    docker-compose up -d postgres redis
    
    # 等待就绪
    log_info "等待数据库和Redis就绪..."
    sleep 15
    
    # 验证服务状态
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
            log_success "PostgreSQL 就绪"
            break
        fi
        [ $i -eq 30 ] && log_error "PostgreSQL 启动超时"
        sleep 2
    done
    
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli -a "${REDIS_PASSWORD:-redis}" ping >/dev/null 2>&1; then
            log_success "Redis 就绪"
            break
        fi
        [ $i -eq 30 ] && log_error "Redis 启动超时"
        sleep 2
    done
    
    # 初始化数据库（通过挂载的脚本自动执行，这里验证并打印表）
    log_info "验证数据库初始化..."
    if docker-compose exec -T postgres psql -U postgres -d ai_postcard -c "SELECT 1;" >/dev/null 2>&1; then
        COUNT=$(docker-compose exec -T postgres psql -U postgres -d ai_postcard -At -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "N/A")
        log_success "数据库连接正常，public 表数量: ${COUNT}"
        log_info "已建表列表:"
        docker-compose exec -T postgres psql -U postgres -d ai_postcard -At -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1;" 2>/dev/null | sed 's/^/  - /'
    else
        log_warning "数据库连接失败或权限异常"
        log_warning "若提示 'global/pg_filenode.map: Permission denied'，通常为数据目录权限问题"
        echo "建议修复："
        echo "  sudo chown -R 999:999 data/postgres"
        echo "  sudo chmod -R u+rwX data/postgres"
        echo "然后重启数据库容器："
        echo "  docker compose down postgres && docker compose up -d postgres"
    fi
    
    # 初始化Redis队列
    log_info "初始化Redis Stream队列..."
    docker-compose exec -T redis redis-cli -a "${REDIS_PASSWORD:-redis}" XGROUP CREATE postcard_tasks ai_agent_workers 0 MKSTREAM >/dev/null 2>&1 || log_info "队列已存在"
    
    log_success "环境初始化完成"
}

# 清理系统
clean() {
    log_warning "这将删除所有容器和数据"
    read -p "确定继续? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker system prune -f
        log_success "清理完成"
    fi
}

# 显示可用的profiles
show_profiles() {
    echo "可用的服务 profiles:"
    echo "  all        - 所有服务"
    echo "  gateway    - API网关"
    echo "  user       - 用户服务"
    echo "  postcard   - 明信片服务"
    echo "  agent      - AI Agent服务"
    echo "  worker     - AI Agent工作进程"
    echo "  user-tests     - 用户服务测试"
    echo "  postcard-tests - 明信片服务测试"
    echo "  agent-tests    - AI Agent测试"
}

# 显示帮助
help() {
    echo "AI 明信片项目 - 统一部署脚本"
    echo ""
    echo "用法:"
    echo "  $0 <command> [options]"
    echo ""
    echo "命令:"
    echo "  build-base                     构建基础镜像"
    echo "  up <profile...>               启动服务"
    echo "  down                          停止服务"
    echo "  restart <service>             重启服务"
    echo "  logs [service] [-f]           查看日志"
    echo "  ps                            查看状态"
    echo "  exec <service> [command]      执行命令"
    echo "  init                          初始化环境"
    echo "  clean                         清理系统"
    echo "  clean-user-data               清理用户数据(保留系统数据)"
    echo "  help                          显示帮助"
    echo ""
    show_profiles
    echo ""
    echo "示例:"
    echo "  $0 up all                     启动所有服务"
    echo "  $0 up gateway user            启动网关和用户服务"
    echo "  $0 logs ai-agent-service -f   查看AI服务实时日志"
    echo "  $0 exec postgres bash         进入数据库容器"
}

# 主函数
main() {
    check_dependencies
    check_env_file
    
    case "${1:-help}" in
        "build-base")
            build_base
            ;;
        "up")
            shift
            up "$@"
            ;;
        "down")
            down
            ;;
        "restart")
            restart "$2"
            ;;
        "logs")
            logs "$2" "$3"
            ;;
        "ps")
            ps
            ;;
        "exec")
            shift
            exec "$@"
            ;;
        "init")
            init
            ;;
        "clean")
            clean
            ;;
        "clean-user-data")
            clean_user_data
            ;;
        "help"|"-h"|"--help")
            help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            help
            exit 1
            ;;
    esac
}

main "$@"
