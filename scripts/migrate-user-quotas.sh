#!/bin/bash
# 用户配额表迁移脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 输出函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================"
echo "     AI明信片 - 用户配额表迁移脚本"
echo "========================================"

# 检查环境变量
if [ ! -f .env ]; then
    log_error ".env文件不存在，请先运行 cp .env.example .env 并配置"
    exit 1
fi

source .env

if [ -z "$DB_PASSWORD" ]; then
    log_error "DB_PASSWORD环境变量未设置"
    exit 1
fi

log_info "开始用户配额表迁移..."

# 检测数据库类型（根据端口号判断）
if [ "${DB_PORT:-5432}" = "5432" ] || [ "${DB_HOST:-postgres}" = "postgres" ]; then
    log_info "检测到PostgreSQL数据库（端口${DB_PORT:-5432}），执行PostgreSQL迁移"
    
    # 使用Docker执行PostgreSQL命令
    if command -v docker >/dev/null 2>&1; then
        log_info "使用Docker执行PostgreSQL迁移"
        docker-compose exec -T postgres psql \
            -U "${DB_USER:-postgres}" \
            -d "${DB_NAME:-ai_postcard}" \
            -f /migrations/add_user_quotas_postgresql.sql 2>/dev/null || \
        docker exec -i $(docker ps -q --filter "name=postgres") psql \
            -U "${DB_USER:-postgres}" \
            -d "${DB_NAME:-ai_postcard}" < src/postcard-service/app/migrations/add_user_quotas_postgresql.sql 2>/dev/null || \
        {
            log_info "Docker方法失败，尝试直接执行SQL"
            # 如果Docker方法失败，尝试直接复制SQL内容
            echo "-- 手动创建用户配额表
CREATE TABLE IF NOT EXISTS user_quotas (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    quota_date DATE NOT NULL,
    generated_count INTEGER DEFAULT 0,
    deleted_count INTEGER DEFAULT 0,
    max_daily_quota INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_date UNIQUE (user_id, quota_date)
);
CREATE INDEX IF NOT EXISTS idx_user_quotas_user_id ON user_quotas(user_id);
CREATE INDEX IF NOT EXISTS idx_user_quotas_quota_date ON user_quotas(quota_date);" | \
            docker exec -i $(docker ps -q --filter "name=postgres") psql \
                -U "${DB_USER:-postgres}" \
                -d "${DB_NAME:-ai_postcard}"
        }
    else
        log_error "Docker不可用，且没有直接的PostgreSQL客户端"
        log_info "请手动执行以下SQL语句："
        echo "================================"
        cat src/postcard-service/app/migrations/add_user_quotas_postgresql.sql
        echo "================================"
        exit 1
    fi
        
else
    log_info "使用MySQL数据库，执行MySQL迁移"
    
    if command -v docker >/dev/null 2>&1; then
        docker exec -i $(docker ps -q --filter "name=mysql") mysql \
            -u "${DB_USER:-root}" \
            -p"$DB_PASSWORD" \
            "${DB_NAME:-ai_postcard}" \
            < src/postcard-service/app/migrations/add_user_quotas.sql
    else
        mysql \
            -h "${DB_HOST:-localhost}" \
            -P "${DB_PORT:-3306}" \
            -u "${DB_USER:-root}" \
            -p"$DB_PASSWORD" \
            "${DB_NAME:-ai_postcard}" \
            < src/postcard-service/app/migrations/add_user_quotas.sql
    fi
fi

if [ $? -eq 0 ]; then
    log_info "✅ 用户配额表迁移完成"
    log_info "表结构："
    log_info "  - user_quotas (id, user_id, quota_date, generated_count, deleted_count, max_daily_quota, created_at, updated_at)"
    log_info "功能："
    log_info "  - 每日生成配额限制：默认2次/天"
    log_info "  - 删除明信片可恢复生成次数"
    log_info "  - 支持管理员调整用户配额"
else
    log_error "❌ 迁移失败"
    exit 1
fi

echo "========================================"