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

# 3. 为 AI Agent 服务创建虚拟环境
log_info "为 AI Agent 服务创建 Python 虚拟环境..."
cd src/ai-agent-service

if [ ! -d .venv ]; then
    python3 -m venv .venv
    log_success "Python 虚拟环境已创建"
else
    log_info "Python 虚拟环境已存在"
fi

# 激活虚拟环境并安装基础依赖
source .venv/bin/activate
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    log_success "Python 依赖已安装"
else
    log_warning "requirements.txt 不存在，跳过依赖安装"
fi
deactivate

cd "$PROJECT_ROOT"

# 4. 为 Gateway 服务安装依赖
log_info "为 Gateway 服务安装 Node.js 依赖..."
cd src/gateway-service

if [ -f package.json ]; then
    npm install
    log_success "Node.js 依赖已安装"
else
    log_warning "package.json 不存在，跳过依赖安装"
fi

cd "$PROJECT_ROOT"

# 5. 创建必要目录
log_info "创建必要目录..."
mkdir -p uploads logs

# 6. 验证环境配置
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
