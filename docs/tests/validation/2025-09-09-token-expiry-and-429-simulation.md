# Token 失效并发模拟与 429 验证手册

目的：验证当小程序端 Token 过期时，是否会因并发请求与重试叠加导致触发后端 429 限流。

## 环境准备

- 按照容器化规范启动：
  - `sh scripts/dev.sh up postcard`（或直接 `docker compose up -d gateway-service user-service postcard-service`）
  - 如调整过依赖，需先 `docker compose build <service>`。
- 确保 Redis、PostgreSQL 依赖随 profile 启动。
- 确保网关透传上游状态码（当前默认开启）。

## 日志位置

- 网关：`logs/gateway/gateway-service.log`
- User Service：`logs/user/user-service.log`
- Postcard Service：`logs/postcard/postcard-service.log`

## 模拟脚本位置

- `tests/integration/token_expiry_simulation.py`

## 运行参数

可通过环境变量控制：

- `BASE_URL`：默认 `http://localhost:8083/api/v1`
- `USER_ID`：默认 `test-user`
- `INITIAL_TOKEN`：默认 `invalid-token`（用于触发 401）
- `REFRESH_TOKEN`：默认空；如提供则会在 401 时尝试刷新
- `CONCURRENCY`：默认 `6`（接近小程序并发上限）
- `BATCH_SIZE`：默认 `6`（一轮包含3个端点，按此重复）
- `ROUNDS`：默认 `1`

## 执行步骤

1) 无刷新场景（仅验证 401 是否放大为 429）：

```bash
cd /Users/elvis/Documents/codes/一个月一个AI项目挑战/2025/8月/ai-postcard
BASE_URL=http://localhost:8083/api/v1 \
USER_ID=test-user \
INITIAL_TOKEN=invalid-token \
python tests/integration/token_expiry_simulation.py | cat
```

预期：
- 大部分为 401，无 429；`refresh_calls` 为 0。

2) 带刷新场景（模拟“单飞刷新 + 重放一次”）：

```bash
cd /Users/elvis/Documents/codes/一个月一个AI项目挑战/2025/8月/ai-postcard
BASE_URL=http://localhost:8083/api/v1 \
USER_ID=test-user \
INITIAL_TOKEN=invalid-token \
REFRESH_TOKEN=<在此填入有效refreshToken> \
CONCURRENCY=6 BATCH_SIZE=12 ROUNDS=2 \
python tests/integration/token_expiry_simulation.py | cat
```

预期：
- 第一次批量请求多为 401 → 触发 1 次刷新（`refresh_calls`: 1）→ 重放后返回 200（或业务成功码）。
- 不应出现显著比例的 429；若出现，需结合响应体 `details.blocked_by` 分析触发维度（user/ip/endpoint/global）。

## 判定标准

- 通过：
  - `status_counts` 中 429 占比极低或为 0；
  - 带刷新场景 `refresh_calls` ≈ 1（单飞生效），重放后大多成功；
  - 服务端日志未出现持续的限流告警（RATE_LIMIT_EXCEEDED）。

- 未通过/需排查：
  - 429 比例显著（>5%）；
  - `refresh_calls` > 1（单飞失效，可能并发触发多次刷新）；
  - 响应 `details.blocked_by` 指向某一特定维度（例如 endpoint），需对该端点在后端放宽或在前端减少并发/重放。

## 常见问题与排查

1. 镜像未重建导致后端仍使用旧的限流参数：
   - 重建并重启：`docker compose build user-service postcard-service && docker compose up -d`

2. 公共端点被无效 Authorization 干扰：
   - 检查后端对公共端点的鉴权策略；或在前端针对非鉴权端点不附带 Authorization。

3. 前端请求风暴：
   - 确认页面 onLoad/onShow 是否重复触发同一请求；
   - 检查任务轮询是否与其它请求叠加过多；
   - 确认 429 不进行自动重试。

## 结束后清理

- 关闭容器释放资源：

```bash
sh scripts/dev.sh down
```


