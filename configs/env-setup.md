# 环境配置说明

## 快速开始

1. **复制环境配置文件**：
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件**，根据你的环境修改配置值

3. **验证配置**：
   ```bash
   sh scripts/dev.sh validate-env  # (脚本创建后可用)
   ```

## 配置分类

### 必需配置
以下配置项必须正确设置才能启动服务：

- `DB_PASSWORD`: 数据库密码
- `REDIS_PASSWORD`: Redis 密码
- `APP_SECRET`: 应用密钥（用于 JWT 等）

### AI 服务配置
如果使用 AI Agent 服务，需要配置：

- `AI_API_KEY`: AI 服务商的 API 密钥
- `AI_BASE_URL`: AI 服务端点（可选）
- `AI_MODEL`: 使用的 AI 模型

### 微信小程序配置
如果需要微信小程序集成：

- `WECHAT_APP_ID`: 微信小程序 AppID
- `WECHAT_APP_SECRET`: 微信小程序 AppSecret

## 环境特定配置

### 开发环境
```bash
NODE_ENV=development
APP_ENV=development
DEBUG=true
HOT_RELOAD=true
```

### 生产环境
```bash
NODE_ENV=production
APP_ENV=production
DEBUG=false
HOT_RELOAD=false

# 使用更安全的密码
DB_PASSWORD=your_secure_production_password
REDIS_PASSWORD=your_secure_redis_password
APP_SECRET=your_secure_app_secret
```

## 安全注意事项

1. **永远不要提交 `.env` 文件**到版本控制
2. **生产环境使用强密码**
3. **定期轮换 API 密钥**
4. **限制数据库和 Redis 的网络访问**

## 配置验证

创建 `scripts/validate-env.sh` 脚本来验证必需的环境变量：

```bash
#!/bin/bash
# 验证必需的环境变量是否已设置

required_vars=(
    "DB_PASSWORD"
    "REDIS_PASSWORD" 
    "APP_SECRET"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ 缺少必需的环境变量："
    printf "   %s\n" "${missing_vars[@]}"
    echo ""
    echo "请检查 .env 文件并设置这些变量。"
    exit 1
else
    echo "✅ 所有必需的环境变量已设置"
fi
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 `DB_*` 配置项
   - 确保 PostgreSQL 容器正在运行

2. **Redis 连接失败**
   - 检查 `REDIS_*` 配置项
   - 确保 Redis 容器正在运行

3. **AI 服务调用失败**
   - 验证 `AI_API_KEY` 是否有效
   - 检查 `AI_BASE_URL` 是否可访问
