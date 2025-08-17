# API 网关设计 (Backend Gateway)

## 1. 职责与核心功能

API 网关是所有客户端请求的唯一入口，其核心职责包括：

- **请求路由 (Request Routing)**: 根据请求的 URL 路径，将请求精确转发到后端的相应微服务。
- **用户认证 (Authentication)**: 拦截并校验所有需要授权的请求，通常通过验证 JWT (JSON Web Token) 来实现。
- **协议转换 (Protocol Translation)**: 可选地，在客户端的 HTTP/REST 协议与后端服务间的 gRPC 等协议之间进行转换。
- **API 聚合 (API Aggregation)**: 将来自多个微服务的调用结果聚合成单个响应，简化客户端交互。
- **全局策略实施**: 如速率限制 (Rate Limiting)、熔断 (Circuit Breaking)、日志记录 (Logging) 和跨域处理 (CORS)。

## 2. 增强设计：可观测性与韧性

### 2.1. 分布式追踪 (Distributed Tracing)

- **机制**: 网关必须为每一个进入系统的外部请求生成一个唯一的 **`Trace ID`** (或沿用上游传入的 `Trace ID`)。
- **实现**: 这个 `Trace ID` 必须通过 HTTP Header（例如 `X-Request-ID`）被注入，并随着请求链路传递到所有下游微服务（用户服务、明信片服务等）。
- **目的**: 在集中式日志系统（如 ELK、Loki）中，可以通过这个 `Trace ID` 聚合一次完整请求的所有相关日志，极大地简化了调试和问题排查。

### 2.2. 健康检查 (Health Checks)

- **网关自身**: 网关需要暴露一个健康检查端点，如 `GET /actuator/health`，供 Kubernetes 的存活探针（Liveness Probe）和就绪探针（Readiness Probe）使用，以实现故障自动重启和流量的平滑切换。
- **下游服务健康检查**: 网关会定期或在路由时检查下游服务的健康状况。如果一个服务实例不健康，网关的负载均衡策略应自动将其从可用列表中移除。

### 2.3. 熔断与降级 (Circuit Breaking & Fallback)

- **熔断器**: 对所有向下游服务的调用，都必须包裹在**熔断器**（如 Resilience4j）中。当某个服务的失败率超过预设阈值时，熔断器会“跳闸”，在一段时间内直接返回错误响应，而不再向该服务发起真实调用，防止故障扩散。
- **服务降级**: 在可能的情况下，可以为熔断的服务提供降级逻辑（Fallback）。例如，如果明信片列表服务暂时不可用，可以返回一个缓存的响应或一个友好的空列表，而不是直接报错。

## 3. 对外暴露的 RESTful API 端点 (Endpoints)

网关将为小程序前端提供以下统一的 API 端点。

### 2.1. 用户认证

- **`POST /api/v1/users/login`**
  - **描述**: 用户通过微信 `code` 换取 `open_id` 和会话 `token`。
  - **请求体**: `{ "code": "wx_login_code" }`
  - **成功响应 (200 OK)**: `{ "token": "jwt_token", "is_new_user": true/false }`
  - **后端服务**: 路由到 `user-service`。

### 2.2. 明信片创作与查询

- **`POST /api/v1/postcards/create`**
  - **描述**: **异步创建**一个新的 AI 明信片。这是启动整个 AI Agent 工作流的入口。
  - **请求体**: `{ "mood": "开心", "style": "赛博朋克", "theme": "...", ... }`
  - **成功响应 (202 Accepted)**: `{ "task_id": "a-unique-identifier-for-the-task" }`
  - **后端交互**:
    1. 验证请求体。
    2. 将包含创作要素的任务消息**发布到消息队列**。
    3. 立即返回 `task_id` 给客户端。

- **`GET /api/v1/postcards/status/{taskId}`**
  - **描述**: **轮询接口**，用于客户端查询异步任务的当前状态。
  - **路径参数**: `taskId` - 从 `create` 接口获取的任务 ID。
  - **成功响应 (200 OK)**:
    - 任务处理中: `{ "status": "processing" }`
    - 任务失败: `{ "status": "failed", "error": "failure_reason" }`
    - 任务完成: `{ "status": "completed", "data": { ...postcard_details... } }`
  - **后端服务**: 路由到 `postcard-service` 进行状态查询。

- **`GET /api/v1/postcards/{postcardId}`**
  - **描述**: 获取单个已完成明信片的详细信息。
  - **路径参数**: `postcardId` - 明信片的唯一标识。
  - **成功响应 (200 OK)**: `{ "postcard_id": "...", "frontend_code": "...", "image_url": "...", ... }`
  - **后端服务**: 路由到 `postcard-service`。

### 2.3. 个人作品集

- **`GET /api/v1/postcards/me`**
  - **描述**: 获取当前登录用户的个人作品集（已生成的明信片列表）。
  - **成功响应 (200 OK)**: `[ { "postcard_id": "...", "image_url": "..." }, ... ]`
  - **后端服务**: 路由到 `postcard-service`。

## 3. 技术选型

- **主要框架**: **Python (FastAPI)**
- **理由**:
  - **高性能**: 基于 Starlette 和 Pydantic，提供极高的异步性能。
  - **开发效率**: 利用 Python 的类型提示，可以自动生成交互式 API 文档（Swagger UI, ReDoc），并进行数据校验。
  - **生态系统**: 拥有庞大的 Python 库支持，可以轻松集成各类工具。
  - **技术栈统一**: 与所有其他后端服务保持一致，降低了维护和学习成本。
- **核心实现机制**:
  - **全局策略**: **FastAPI 中间件 (Middleware)** 将是实现分布式追踪、日志记录、CORS 处理和全局异常捕获的核心。
  - **熔断器**: 可选用 `pybreaker` 等成熟的 Python 库来实现熔断逻辑。
  - **分布式追踪**: 可集成 OpenTelemetry 等开源标准库，通过中间件自动注入和传递 `Trace ID`。 