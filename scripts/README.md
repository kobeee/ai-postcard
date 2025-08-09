# 开发脚本说明

本目录包含用于管理 AI 明信片项目开发环境的脚本。

## 脚本列表

### `dev.sh` - 主要管理脚本
统一管理 Docker Compose 服务的启动、停止和监控。

**基础用法：**
```bash
# 启动服务
sh scripts/dev.sh up gateway user      # 启动网关和用户服务
sh scripts/dev.sh up agent             # 启动 AI Agent 服务

# 停止服务
sh scripts/dev.sh down

# 查看日志
sh scripts/dev.sh logs                 # 所有服务日志
sh scripts/dev.sh logs gateway-service # 特定服务日志

# 其他命令
sh scripts/dev.sh ps                   # 查看服务状态
sh scripts/dev.sh restart gateway-service
sh scripts/dev.sh help                 # 查看完整帮助
```

**场景化启动示例：**
```bash
# 开发网关服务
sh scripts/dev.sh up gateway

# 开发用户服务（需要数据库）
sh scripts/dev.sh up user

# 运行 AI Agent 测试
sh scripts/dev.sh up agent-tests

# 执行 AI Agent 脚本
export SCRIPT_COMMAND="python scripts/data_migration.py"
sh scripts/dev.sh up agent-script
```

### `validate-env.sh` - 环境验证脚本
验证 `.env` 文件中的环境变量是否正确设置。

```bash
sh scripts/validate-env.sh
```

### `setup-dev-env.sh` - 开发环境初始化脚本
自动设置完整的开发环境，包括：
- 检查必要工具
- 创建 `.env` 文件
- 创建 Python 虚拟环境
- 安装依赖（如果存在配置文件）

```bash
sh scripts/setup-dev-env.sh
```

## 工作流示例

### 首次设置
```bash
# 1. 初始化开发环境
sh scripts/setup-dev-env.sh

# 2. 编辑环境配置
vi .env

# 3. 验证配置
sh scripts/validate-env.sh

# 4. 启动基础服务
sh scripts/dev.sh up gateway user
```

### 日常开发
```bash
# 启动需要的服务
sh scripts/dev.sh up agent

# 查看日志
sh scripts/dev.sh logs ai-agent-service

# 进入容器调试
sh scripts/dev.sh exec ai-agent-service bash

# 停止服务
sh scripts/dev.sh down
```

### 运行测试
```bash
# 运行特定服务的测试
sh scripts/dev.sh up user-tests
sh scripts/dev.sh up agent-tests

# 查看测试日志
sh scripts/dev.sh logs ai-postcard-agent-tests
```

## 故障排除

### 常见问题

1. **脚本权限错误**
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Docker 未运行**
   ```bash
   # macOS
   open -a Docker
   
   # Linux
   sudo systemctl start docker
   ```

3. **端口冲突**
   检查 `.env` 文件中的端口配置，确保没有被其他服务占用。

4. **依赖安装失败**
   确保已安装 Node.js、Python 3 和相关包管理器。

### 日志查看
```bash
# 实时查看所有服务日志
sh scripts/dev.sh logs

# 查看特定服务日志
sh scripts/dev.sh logs postgres-db
sh scripts/dev.sh logs redis-cache

# 查看最近的日志（不跟踪）
docker-compose logs --tail=50 gateway-service
```

### 清理和重置
```bash
# 停止所有服务
sh scripts/dev.sh down

# 清理所有容器和卷（⚠️ 数据会丢失）
sh scripts/dev.sh clean

# 重新构建镜像
sh scripts/dev.sh up gateway --build
```
