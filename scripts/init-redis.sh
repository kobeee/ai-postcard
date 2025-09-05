#!/bin/bash

# =============================================================================
# AI 明信片项目 - Redis 初始化脚本
# =============================================================================
# 功能：初始化 Redis 缓存结构、消息队列和消费者组
# 用法：sh scripts/init-redis.sh [--force] [--password=<password>]
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 默认参数
FORCE_INIT=false
REDIS_PASSWORD=""
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_CONTAINER="ai-postcard-redis"

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --force)
            FORCE_INIT=true
            shift
            ;;
        --password=*)
            REDIS_PASSWORD="${arg#*=}"
            shift
            ;;
        --host=*)
            REDIS_HOST="${arg#*=}"
            shift
            ;;
        --port=*)
            REDIS_PORT="${arg#*=}"
            shift
            ;;
        --container=*)
            REDIS_CONTAINER="${arg#*=}"
            shift
            ;;
        -h|--help)
            echo "用法: $0 [--force] [--password=<password>] [--host=<host>] [--port=<port>]"
            echo "  --force                强制重新初始化"
            echo "  --password=<password>  Redis密码"
            echo "  --host=<host>         Redis主机 (默认: localhost)"
            echo "  --port=<port>         Redis端口 (默认: 6379)"
            echo "  --container=<name>     Redis容器名称 (默认: ai-postcard-redis)"
            echo "  --help                 显示帮助信息"
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

# 从环境变量获取Redis密码
get_redis_password() {
    if [ -z "$REDIS_PASSWORD" ]; then
        if [ -f .env ]; then
            REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        fi
        
        if [ -z "$REDIS_PASSWORD" ]; then
            REDIS_PASSWORD="redis"  # 默认密码
            log_warning "未找到Redis密码，使用默认值"
        fi
    fi
}

# Redis命令执行函数
redis_exec() {
    local cmd="$1"
    local use_auth="$2"
    
    if [ "$use_auth" = "true" ] && [ -n "$REDIS_PASSWORD" ]; then
        if command -v docker &> /dev/null && docker ps | grep -q "$REDIS_CONTAINER"; then
            docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" $cmd 2>/dev/null
        else
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" $cmd 2>/dev/null
        fi
    else
        if command -v docker &> /dev/null && docker ps | grep -q "$REDIS_CONTAINER"; then
            docker exec "$REDIS_CONTAINER" redis-cli $cmd 2>/dev/null
        else
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" $cmd 2>/dev/null
        fi
    fi
}

# 检查Redis连接
check_redis_connection() {
    log_info "检查Redis连接..."
    
    get_redis_password
    
    if redis_exec "PING" true | grep -q "PONG"; then
        log_success "Redis连接正常"
        return 0
    elif redis_exec "PING" false | grep -q "PONG"; then
        log_success "Redis连接正常（无密码）"
        REDIS_PASSWORD=""
        return 0
    else
        log_error "无法连接到Redis服务器"
        log_error "请确保Redis服务正在运行，主机和端口配置正确"
        return 1
    fi
}

# 初始化消息队列
init_message_queues() {
    log_info "初始化Redis Streams消息队列..."
    
    # 定义队列和消费者组配置
    local QUEUE_STREAM_NAME="postcard_tasks"
    local QUEUE_CONSUMER_GROUP="ai_agent_workers" 
    
    # 从环境变量读取配置（如果存在）
    if [ -f .env ]; then
        local env_stream=$(grep '^QUEUE_STREAM_NAME=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        local env_group=$(grep '^QUEUE_CONSUMER_GROUP=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        
        [ -n "$env_stream" ] && QUEUE_STREAM_NAME="$env_stream"
        [ -n "$env_group" ] && QUEUE_CONSUMER_GROUP="$env_group"
    fi
    
    log_info "队列配置: Stream=$QUEUE_STREAM_NAME, Group=$QUEUE_CONSUMER_GROUP"
    
    # 检查Stream是否存在
    if redis_exec "EXISTS $QUEUE_STREAM_NAME" true | grep -q "1"; then
        log_info "Stream $QUEUE_STREAM_NAME 已存在"
        
        if [ "$FORCE_INIT" = true ]; then
            log_warning "强制模式：删除现有Stream和消费者组"
            
            # 删除消费者组
            redis_exec "XGROUP DESTROY $QUEUE_STREAM_NAME $QUEUE_CONSUMER_GROUP" true >/dev/null 2>&1 || true
            
            # 删除Stream中的所有消息（保留Stream结构）
            redis_exec "XTRIM $QUEUE_STREAM_NAME MAXLEN 0" true >/dev/null 2>&1 || true
            
            log_info "Stream清理完成"
        fi
    fi
    
    # 创建消费者组（如果不存在）
    if redis_exec "XGROUP CREATE $QUEUE_STREAM_NAME $QUEUE_CONSUMER_GROUP 0 MKSTREAM" true >/dev/null 2>&1; then
        log_success "消费者组 $QUEUE_CONSUMER_GROUP 创建成功"
    else
        # 检查是否是因为组已存在而失败
        if redis_exec "XINFO GROUPS $QUEUE_STREAM_NAME" true | grep -q "$QUEUE_CONSUMER_GROUP"; then
            log_info "消费者组 $QUEUE_CONSUMER_GROUP 已存在"
        else
            log_warning "消费者组创建失败，可能需要手动处理"
        fi
    fi
    
    # 验证设置
    local stream_exists=$(redis_exec "EXISTS $QUEUE_STREAM_NAME" true)
    if [ "$stream_exists" = "1" ]; then
        log_success "消息队列初始化完成"
        
        # 显示队列信息
        local stream_length=$(redis_exec "XLEN $QUEUE_STREAM_NAME" true)
        log_info "队列当前消息数量: $stream_length"
    else
        log_error "消息队列初始化失败"
        return 1
    fi
}

# 初始化缓存结构
init_cache_structure() {
    log_info "初始化缓存结构..."
    
    # 清理过期的缓存数据（如果强制初始化）
    if [ "$FORCE_INIT" = true ]; then
        log_info "清理现有缓存数据..."
        
        # 清理各种类型的缓存
        local cache_patterns=("cache:*" "session:*" "temp:*" "lock:*")
        
        for pattern in "${cache_patterns[@]}"; do
            local keys=$(redis_exec "KEYS $pattern" true)
            if [ -n "$keys" ]; then
                echo "$keys" | xargs -r redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" DEL >/dev/null 2>&1 || true
                log_info "清理缓存模式: $pattern"
            fi
        done
    fi
    
    # 设置缓存配置
    redis_exec "CONFIG SET maxmemory-policy allkeys-lru" true >/dev/null 2>&1 || {
        log_warning "无法设置内存策略，可能需要管理员权限"
    }
    
    # 创建一些基础的缓存键（用于测试）
    redis_exec "SET cache:init_test 'Redis缓存初始化完成' EX 3600" true >/dev/null 2>&1
    
    log_success "缓存结构初始化完成"
}

# 初始化性能监控
init_monitoring() {
    log_info "初始化性能监控配置..."
    
    # 启用Redis慢查询日志
    redis_exec "CONFIG SET slowlog-log-slower-than 10000" true >/dev/null 2>&1 || {
        log_warning "无法设置慢查询日志，可能需要管理员权限"
    }
    
    redis_exec "CONFIG SET slowlog-max-len 128" true >/dev/null 2>&1 || true
    
    log_success "监控配置完成"
}

# 验证初始化结果
verify_initialization() {
    log_info "验证初始化结果..."
    
    # 检查基本连接
    if ! redis_exec "PING" true | grep -q "PONG"; then
        log_error "Redis连接验证失败"
        return 1
    fi
    
    # 检查消息队列
    local stream_exists=$(redis_exec "EXISTS postcard_tasks" true)
    if [ "$stream_exists" != "1" ]; then
        log_error "消息队列验证失败"
        return 1
    fi
    
    # 检查缓存测试键
    if redis_exec "EXISTS cache:init_test" true | grep -q "1"; then
        log_success "缓存功能验证通过"
    else
        log_warning "缓存测试键不存在"
    fi
    
    # 显示Redis信息
    local redis_version=$(redis_exec "INFO server" true | grep "redis_version" | cut -d':' -f2 | tr -d '\r')
    local used_memory=$(redis_exec "INFO memory" true | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r')
    local connected_clients=$(redis_exec "INFO clients" true | grep "connected_clients" | cut -d':' -f2 | tr -d '\r')
    
    log_success "Redis初始化验证完成"
    echo ""
    echo "Redis服务信息："
    echo "  版本: $redis_version"
    echo "  内存使用: $used_memory"
    echo "  连接客户端: $connected_clients"
    echo ""
}

# 显示使用说明
show_usage_info() {
    echo "Redis初始化完成，可用的功能："
    echo ""
    echo "消息队列："
    echo "  - Stream: postcard_tasks"
    echo "  - Consumer Group: ai_agent_workers" 
    echo ""
    echo "缓存命名空间："
    echo "  - cache:*    应用缓存"
    echo "  - session:*  会话数据"
    echo "  - temp:*     临时数据"
    echo "  - lock:*     分布式锁"
    echo ""
    echo "监控命令："
    echo "  - 查看队列长度: XLEN postcard_tasks"
    echo "  - 查看消费者组: XINFO GROUPS postcard_tasks"
    echo "  - 查看慢查询: SLOWLOG GET 10"
    echo "  - 查看内存使用: INFO memory"
    echo ""
}

# 主函数
main() {
    echo -e "${BLUE}"
    echo "=============================================================================="
    echo "                         Redis 初始化"
    echo "=============================================================================="
    echo -e "${NC}"
    echo "强制重新初始化: $FORCE_INIT"
    echo "Redis主机: $REDIS_HOST:$REDIS_PORT"
    echo ""
    
    if ! check_redis_connection; then
        exit 1
    fi
    
    init_message_queues
    init_cache_structure
    init_monitoring
    verify_initialization
    show_usage_info
    
    echo -e "${GREEN}"
    echo "=============================================================================="
    echo "                         Redis初始化完成！"
    echo "=============================================================================="
    echo -e "${NC}"
}

# 运行主函数
main "$@"