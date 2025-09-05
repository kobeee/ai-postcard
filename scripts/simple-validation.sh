#!/bin/bash

# =============================================================================
# AI 明信片项目 - 简化部署验证脚本
# =============================================================================

set -e

echo "===================================================="
echo "AI 明信片项目部署系统验证开始..."
echo "===================================================="

# 计数器
PASS=0
FAIL=0

# 测试函数
test_pass() {
    echo "✅ PASS: $1"
    ((PASS++))
}

test_fail() {
    echo "❌ FAIL: $1"
    ((FAIL++))
}

echo ""
echo "1. 验证核心配置文件..."

# 验证配置文件
[ -f ".env" ] && test_pass ".env 文件存在" || test_fail ".env 文件不存在"
[ -f "docker-compose.yml" ] && test_pass "docker-compose.yml 存在" || test_fail "docker-compose.yml 不存在"
[ -f "docker-compose.prod.yml" ] && test_pass "docker-compose.prod.yml 存在" || test_fail "docker-compose.prod.yml 不存在"

# 验证Docker Compose配置
if docker-compose -f docker-compose.prod.yml config --quiet >/dev/null 2>&1; then
    test_pass "docker-compose.prod.yml 配置正确"
else
    test_fail "docker-compose.prod.yml 配置有误"
fi

echo ""
echo "2. 验证管理脚本..."

# 验证脚本存在性和语法
scripts=("init-project.sh" "init-redis.sh" "dev.sh" "prod.sh")
for script in "${scripts[@]}"; do
    if [ -f "scripts/$script" ]; then
        if bash -n "scripts/$script" 2>/dev/null; then
            test_pass "scripts/$script 语法正确"
        else
            test_fail "scripts/$script 语法错误"
        fi
    else
        test_fail "scripts/$script 不存在"
    fi
done

echo ""
echo "3. 验证Dockerfile文件..."

# 验证Dockerfile
services=("gateway-service" "user-service" "postcard-service" "ai-agent-service")
for service in "${services[@]}"; do
    dockerfile="src/$service/Dockerfile"
    if [ -f "$dockerfile" ]; then
        if grep -q "FROM" "$dockerfile" && grep -q "WORKDIR" "$dockerfile"; then
            test_pass "$service Dockerfile 结构正确"
        else
            test_fail "$service Dockerfile 结构不完整"
        fi
    else
        test_fail "$service Dockerfile 不存在"
    fi
done

echo ""
echo "4. 验证环境变量..."

# 验证环境变量
if source .env 2>/dev/null; then
    required_vars=("DB_PASSWORD" "REDIS_PASSWORD" "APP_SECRET" "ANTHROPIC_AUTH_TOKEN")
    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            test_pass "$var 已配置"
        else
            test_fail "$var 未配置"
        fi
    done
else
    test_fail ".env 文件格式错误"
fi

echo ""
echo "5. 验证Docker Compose服务定义..."

# 验证服务定义
if docker-compose -f docker-compose.prod.yml --profile all config --services >/dev/null 2>&1; then
    services_count=$(docker-compose -f docker-compose.prod.yml --profile all config --services 2>/dev/null | wc -l)
    if [ "$services_count" -ge 6 ]; then
        test_pass "所有服务定义正确 (共$services_count个服务)"
    else
        test_fail "服务定义不完整 (仅$services_count个服务)"
    fi
else
    test_fail "服务定义验证失败"
fi

echo ""
echo "6. 验证关键命令..."

# 验证关键命令
if sh scripts/prod.sh help >/dev/null 2>&1; then
    test_pass "prod.sh help 命令正常"
else
    test_fail "prod.sh help 命令失败"
fi

echo ""
echo "===================================================="
echo "验证结果:"
echo "  通过: $PASS"
echo "  失败: $FAIL"
echo "===================================================="

if [ $FAIL -eq 0 ]; then
    echo "🎉 验证成功！所有检查都通过了！"
    echo ""
    echo "推荐的部署命令:"
    echo "  1. 构建镜像: docker-compose -f docker-compose.prod.yml --profile all build --no-cache"
    echo "  2. 启动服务: sh scripts/prod.sh up all"
    echo "  3. 查看状态: sh scripts/prod.sh ps"
    exit 0
else
    echo "❌ 验证失败！发现 $FAIL 个问题需要修复。"
    exit 1
fi