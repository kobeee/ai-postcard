#!/bin/bash

# =============================================================================
# 环境变量验证脚本
# =============================================================================
# 验证必需的环境变量是否已正确设置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 检查 .env 文件
if [ ! -f .env ]; then
    log_error ".env 文件不存在"
    log_info "请运行: cp .env.example .env"
    exit 1
fi

# 加载环境变量
export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

# 必需的环境变量
required_vars=(
    "DB_PASSWORD"
    "REDIS_PASSWORD"
    "APP_SECRET"
)

# 推荐设置的环境变量
recommended_vars=(
    "AI_API_KEY"
    "WECHAT_APP_ID"
    "WECHAT_APP_SECRET"
)

# 检查必需变量
missing_required=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_required+=("$var")
    fi
done

# 检查推荐变量
missing_recommended=()
for var in "${recommended_vars[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" =~ ^your_.*_here$ ]]; then
        missing_recommended+=("$var")
    fi
done

# 输出结果
if [ ${#missing_required[@]} -gt 0 ]; then
    log_error "缺少必需的环境变量："
    printf "   %s\n" "${missing_required[@]}"
    exit 1
fi

if [ ${#missing_recommended[@]} -gt 0 ]; then
    log_warning "建议设置以下环境变量："
    printf "   %s\n" "${missing_recommended[@]}"
fi

log_info "✅ 环境变量验证通过"

# 检查数据库连接格式
if [[ ! "$DATABASE_URL" =~ ^postgresql:// ]] && [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then
    log_info "数据库连接配置: postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
fi

# 检查 Redis 连接格式
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PASSWORD" ]; then
    log_info "Redis 连接配置: redis://:***@$REDIS_HOST:$REDIS_PORT/0"
fi
