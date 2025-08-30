#!/bin/bash
# 更新用户配额逻辑 - 数据库迁移脚本

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
echo "     更新用户配额逻辑迁移脚本"
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

log_info "开始更新用户配额表结构..."

# 使用Docker执行PostgreSQL命令
if command -v docker >/dev/null 2>&1; then
    log_info "使用Docker执行PostgreSQL迁移"
    
    # 直接执行SQL内容
    echo "-- 更新用户配额表结构
BEGIN;

-- 删除旧的 deleted_count 列（如果存在）  
ALTER TABLE user_quotas DROP COLUMN IF EXISTS deleted_count;

-- 添加新的 current_card_exists 列
ALTER TABLE user_quotas ADD COLUMN IF NOT EXISTS current_card_exists BOOLEAN DEFAULT FALSE;

-- 添加今日卡片ID引用
ALTER TABLE user_quotas ADD COLUMN IF NOT EXISTS current_card_id VARCHAR(255) DEFAULT NULL;

-- 创建索引优化查询
CREATE INDEX IF NOT EXISTS idx_user_quotas_card_exists ON user_quotas(user_id, quota_date, current_card_exists);

COMMIT;" | \
    docker exec -i $(docker ps -q --filter "name=postgres") psql \
        -U "${DB_USER:-postgres}" \
        -d "${DB_NAME:-ai_postcard}"
else
    log_error "Docker不可用"
    exit 1
fi

if [ $? -eq 0 ]; then
    log_info "✅ 用户配额表结构更新完成"
    log_info "更新内容："
    log_info "  - 删除: deleted_count 列"
    log_info "  - 添加: current_card_exists 列（追踪当前是否有卡片）"
    log_info "  - 添加: current_card_id 列（当前卡片ID引用）"
    log_info "  - 添加: 索引优化查询性能"
    log_info ""
    log_info "新的配额逻辑："
    log_info "  - 每日最多生成2次（总生成次数）"
    log_info "  - 删除卡片释放位置，不恢复生成次数"
    log_info "  - 判断规则：can_generate = (generated_count < 2) AND (NOT current_card_exists)"
else
    log_error "❌ 迁移失败"
    exit 1
fi

echo "========================================"