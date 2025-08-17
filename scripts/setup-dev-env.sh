#!/bin/bash

# =============================================================================
# 开发环境初始化脚本
# =============================================================================
# 自动设置开发环境，包括依赖安装和初始化

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "开始设置 AI 明信片项目开发环境..."

# 1. 检查必要工具
log_info "检查必要工具..."
required_tools=("docker" "docker-compose" "node" "python3")
missing_tools=()

for tool in "${required_tools[@]}"; do
    if ! command -v $tool &> /dev/null; then
        missing_tools+=("$tool")
    fi
done

if [ ${#missing_tools[@]} -gt 0 ]; then
    log_error "缺少必要工具："
    printf "   %s\n" "${missing_tools[@]}"
    echo ""
    log_error "请安装这些工具后再运行此脚本"
    exit 1
fi

log_success "所有必要工具已安装"

# 2. 创建 .env 文件
if [ ! -f .env ]; then
    log_info "创建 .env 文件..."
    cp .env.example .env
    log_success ".env 文件已创建"
    log_warning "请编辑 .env 文件并设置正确的配置值"
else
    log_info ".env 文件已存在"
fi

# 3. 遍历 src 目录下的所有服务并设置环境
log_info "开始为所有微服务设置开发环境..."

for service_dir in src/*/; do
    service_name=$(basename "$service_dir")
    
    log_info "正在处理服务: '${service_name}'"

    if [ -f "${service_dir}requirements.txt" ]; then
        cd "$service_dir"
        log_info "  -> 检测到 Python 服务，设置虚拟环境..."
        
        # 检查虚拟环境是否完整，如果不完整则重建
        if [ ! -f ".venv/bin/activate" ]; then
            log_warning "    - '.venv' 不完整或 'activate' 脚本不存在，将重建虚拟环境..."
            rm -rf .venv
            python3 -m venv .venv
            log_success "    - 虚拟环境已成功重建"
        else
            log_info "    - 虚拟环境已存在且有效"
        fi
        
        source .venv/bin/activate
        pip install -r requirements.txt
        deactivate
        log_success "    - Python 依赖已安装"

    elif [ -f "${service_dir}package.json" ]; then
        cd "$service_dir"
        log_info "  -> 检测到 Node.js 服务，安装依赖..."
        npm install
        log_success "    - Node.js 依赖已安装"
    else
        log_warning "  -> 在 '${service_name}' 中未找到 'requirements.txt' 或 'package.json'，跳过。"
    fi
    
    # 每次循环结束后返回项目根目录
    cd "$PROJECT_ROOT"
done

# 确保最后返回项目根目录
cd "$PROJECT_ROOT"

# 4. 创建必要目录
log_info "创建必要目录..."
mkdir -p uploads logs

# 5. 验证环境配置
log_info "验证环境配置..."
if [ -x scripts/validate-env.sh ]; then
    ./scripts/validate-env.sh
else
    log_warning "环境验证脚本不存在或不可执行"
fi

log_success "开发环境初始化完成！"
echo ""
log_info "接下来可以运行以下命令启动服务："
echo "  sh scripts/dev.sh up gateway user    # 启动网关和用户服务"
echo "  sh scripts/dev.sh up agent          # 启动 AI Agent 服务"
echo ""
log_info "查看更多命令："
echo "  sh scripts/dev.sh help"
