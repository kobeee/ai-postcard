#!/bin/bash

# =============================================================================
# Docker镜像拉取超时问题 - 自动修复脚本
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Docker镜像拉取超时问题 - 自动修复脚本${NC}"
echo "=================================================="

# 检查Docker是否运行
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker未运行，请先启动Docker Desktop${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker服务运行正常${NC}"
}

# 清理Docker缓存
clean_docker_cache() {
    echo -e "${YELLOW}🧹 清理Docker构建缓存...${NC}"
    docker builder prune -f >/dev/null 2>&1 || true
    echo -e "${GREEN}✅ Docker缓存已清理${NC}"
}

# 测试镜像拉取
test_image_pull() {
    local image=$1
    echo -e "${BLUE}🔍 测试镜像: $image${NC}"
    
    if timeout 60 docker pull "$image" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $image 拉取成功${NC}"
        return 0
    else
        echo -e "${RED}❌ $image 拉取失败${NC}"
        return 1
    fi
}

# 主修复流程
main_fix() {
    echo ""
    echo -e "${BLUE}开始修复流程...${NC}"
    
    # 检查Docker
    check_docker
    
    # 清理缓存
    clean_docker_cache
    
    # 测试关键镜像
    echo ""
    echo -e "${BLUE}🔍 测试关键镜像拉取...${NC}"
    
    local images=(
        "node:20-slim"
        "python:3.11-slim" 
        "nginx:alpine"
        "redis:7-alpine"
        "postgres:15-alpine"
    )
    
    local failed_images=()
    
    for image in "${images[@]}"; do
        if ! test_image_pull "$image"; then
            failed_images+=("$image")
        fi
    done
    
    if [ ${#failed_images[@]} -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 所有镜像测试通过！${NC}"
        echo -e "${GREEN}现在可以安全地运行构建命令：${NC}"
        echo -e "${BLUE}docker-compose -f docker-compose.prod.yml --profile all build --no-cache${NC}"
        return 0
    else
        echo ""
        echo -e "${YELLOW}⚠️  以下镜像仍然有问题：${NC}"
        for img in "${failed_images[@]}"; do
            echo -e "${RED}  - $img${NC}"
        done
        
        echo ""
        echo -e "${YELLOW}🔄 尝试备用方案...${NC}"
        
        # 备用方案：使用镜像加速器手动拉取
        for img in "${failed_images[@]}"; do
            echo -e "${BLUE}尝试从镜像加速器拉取: $img${NC}"
            
            local mirrors=(
                "docker.m.daocloud.io/library"
                "hub.rat.dev"
            )
            
            for mirror in "${mirrors[@]}"; do
                echo -e "${BLUE}  从 $mirror 拉取...${NC}"
                if timeout 60 docker pull "$mirror/$img" >/dev/null 2>&1; then
                    docker tag "$mirror/$img" "$img"
                    echo -e "${GREEN}✅ $img 从 $mirror 拉取成功${NC}"
                    break
                fi
            done
        done
    fi
}

# 验证修复结果
verify_fix() {
    echo ""
    echo -e "${BLUE}🔍 验证修复结果...${NC}"
    
    # 尝试构建测试（dry-run）
    if docker-compose -f docker-compose.prod.yml --profile all build --dry-run >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 构建配置验证通过${NC}"
        echo ""
        echo -e "${GREEN}🎉 修复成功！现在可以运行：${NC}"
        echo -e "${BLUE}docker-compose -f docker-compose.prod.yml --profile all build --no-cache${NC}"
    else
        echo -e "${RED}❌ 构建配置仍有问题${NC}"
        echo ""
        echo -e "${YELLOW}💡 建议：${NC}"
        echo -e "${YELLOW}1. 重启Docker Desktop${NC}"
        echo -e "${YELLOW}2. 检查网络连接${NC}"
        echo -e "${YELLOW}3. 查看详细指南: cat docker-fix-guide.md${NC}"
    fi
}

# 显示系统信息
show_system_info() {
    echo ""
    echo -e "${BLUE}📊 系统信息：${NC}"
    echo "Docker版本: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '无法获取')"
    echo "操作系统: $(uname -s)"
    
    if docker info | grep -q "Registry Mirrors"; then
        echo -e "${GREEN}✅ 镜像加速器已配置${NC}"
    else
        echo -e "${YELLOW}⚠️  未检测到镜像加速器配置${NC}"
    fi
}

# 执行修复
echo ""
show_system_info
main_fix
verify_fix

echo ""
echo -e "${BLUE}修复脚本执行完成！${NC}"
echo "=================================================="