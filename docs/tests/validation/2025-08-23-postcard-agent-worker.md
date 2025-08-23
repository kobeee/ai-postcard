# 2025-08-23 异步工作流回归测试与验证步骤

本文档用于验证本次修复后，worker、Redis 与 postcard-service 的稳定性与功能完整性。

## 1. 环境准备与启动

1) 关闭已有容器（如果在运行）：
```
sh scripts/dev.sh down
```

2) 强制重建并启动核心服务：
```
FORCE_REBUILD=true sh scripts/dev.sh up postcard agent worker
```

3) 查看服务状态：
```
sh scripts/dev.sh ps
```

预期：postgres、redis、postcard-service、ai-agent-service、ai-agent-worker 均为 Up 状态。

## 2. 日志查看位置

- postcard-service 文件日志：`src/postcard-service/logs/postcard-service.log`
- gateway-service 文件日志：`src/gateway-service/logs/gateway-service.log`
- user-service 文件日志：`src/user-service/logs/user-service.log`
- ai-agent-service/worker：当前主要通过容器控制台查看（compose 中已挂载 `./src/ai-agent-service/logs:/app/logs`，如需文件日志可后续开启）

快速查看：
```
tail -n 100 -f src/postcard-service/logs/postcard-service.log
```

容器日志：
```
sh scripts/dev.sh logs ai-postcard-postcard-service
sh scripts/dev.sh logs ai-postcard-ai-agent-worker
```

## 3. 健康检查

- Postcard Service：
```
curl -s http://localhost:8082/health | jq
```
预期：`{"status":"healthy","service":"postcard-service",...}`

- AI Agent Service（如需）：
```
curl -s http://localhost:8080/health-check | jq
```

## 4. 创建测试任务

发送创建任务请求：
```
curl -s http://localhost:8082/api/v1/postcards/create \
 -H "Content-Type: application/json" \
 -d '{"user_input":"为生日做一张可爱的动态贺卡","style":"cute","theme":"birthday"}' | jq
```

记录返回的 `task_id`。

## 5. 观察 worker 消费任务

查看 worker 日志：
```
sh scripts/dev.sh logs ai-postcard-ai-agent-worker
```
预期：
- 连接 Redis 成功：`✅ Redis连接成功`
- 创建/存在消费者组：`✅ 消费者组创建成功` 或 `✅ 消费者组已存在`
- 收到任务并开始执行：`📨 收到任务: ...`、`📋 任务详情: ...`

## 6. 任务状态查询

用 `task_id` 查询状态：
```
curl -s "http://localhost:8082/api/v1/postcards/status/<task_id>" | jq
```
预期：`status` 从 `pending` → `processing` → `completed`；失败时为 `failed` 并含 `error_message`。

## 7. 常见问题排查

- Redis 消费者组已存在报错：
  - 现已正确捕获 `ResponseError`，日志显示“消费者组已存在”后服务继续运行。

- 数据库连接失败：
  - 确认 `.env` 中 `DB_HOST=postgres`、`DB_PASSWORD` 与 compose 一致。
  - 重建并启动 `postcard-service`：
    ```
    docker-compose build postcard-service
    sh scripts/dev.sh down
    sh scripts/dev.sh up postcard
    ```

- worker 退出：
  - 确认 `.env` 中 `REDIS_PASSWORD=redis` 且 `REDIS_URL=redis://redis:6379`。
  - 重启相关容器：
    ```
    sh scripts/dev.sh restart ai-postcard-ai-agent-service
    sh scripts/dev.sh restart ai-postcard-ai-agent-worker
    ```

## 8. 图片生成模型配置与常见错误

- 如果日志出现 `The requested combination of response modalities (TEXT) is not supported by the model`：
  - 请确认 `env.example` / `.env` 中 `GEMINI_IMAGE_MODEL` 是否为支持图像输出的模型（例如：`gemini-2.0-flash-preview-image-generation`）。
  - 未配置 `GEMINI_API_KEY` 时系统将自动使用占位图，不影响流程验证。
  - 如需真实图片，请配置有效的 `GEMINI_API_KEY` 并重建镜像。

## 9. 遇到数据验证错误（dict_type）时的处理

- 现象：worker 日志出现 `metadata Input should be a valid dictionary [dict_type]`
- 原因：队列消息中的 `metadata` 被序列化为了字符串。
- 处理：已在发布端清洗 None 并规范化类型，在消费端自动 `json.loads` 转换 `metadata`；如仍出现，请检查 Redis 中该条消息的字段是否为字符串 `'{}'`，必要时清理历史消息后重新验证。

## 10. 收尾与清理

测试完成后关闭环境：
```
sh scripts/dev.sh down
```

保留数据卷（默认），如需彻底清理：
```
docker-compose down -v --remove-orphans
```
