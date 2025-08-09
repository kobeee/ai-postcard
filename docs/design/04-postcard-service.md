# 明信片服务设计 (Postcard Service)

## 1. 核心职责

明信片服务是系统中所有明信片数据的权威来源和管理者。在新的异步架构下，其核心职责转变为：

- **数据持久化**: 存储由 AI Agent 服务最终生成的明信片数据，包括 `frontend_code`, `image_url` 等核心内容。
- **任务状态管理**: 跟踪和更新异步生成任务的状态。这是实现客户端轮询的关键。
- **数据查询**: 提供对已完成明信片数据的查询接口，包括单个查询和列表查询（如个人作品集）。
- **数据聚合**: 可选地，在返回数据时聚合相关的用户信息（通过调用用户服务）。

## 2. 数据模型 (Data Model)

- **`Postcards` Table**
  - `postcard_id` (BIGINT, Primary Key, Auto-increment)
  - `user_id` (BIGINT, Foreign Key, Not Null): 关联到 `Users` 表。
  - `frontend_code` (TEXT): 存储由 AI 生成的、用于渲染的完整前端代码。
  - `image_url` (VARCHAR): 原始图片素材的 URL。
  - `copywriting_text` (TEXT): 原始文案素材。
  - `generation_params` (JSONB): 生成该卡片的所有输入参数。
  - `created_at` (TIMESTAMP)

- **`Tasks` Table (新增)**
  - `task_id` (VARCHAR, Primary Key): 任务的唯一标识符，由网关或服务自身在启动时生成。
  - `postcard_id` (BIGINT, Nullable): 任务成功后关联到的明信片 ID。
  - `status` (VARCHAR): 任务状态，例如 `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`。
  - `error_message` (TEXT): 任务失败时的错误信息。
  - `created_at` (TIMESTAMP)
  - `updated_at` (TIMESTAMP)
  - `user_id` (BIGINT, Not Null): 关联到 `Users` 表。

  *注：`Tasks` 表用于解耦任务跟踪和最终数据存储，让状态查询更高效。*

## 3. 服务间接口 (Inter-Service API)

- **`rpc CreateTask (CreateTaskRequest) returns (CreateTaskResponse)`**
  - **描述**: 在接收到来自消息队列的创建指令后，创建一个初始任务记录。
  - **请求**: `{ task_id: "...", user_id: 123, generation_params: {...} }`
  - **响应**: `{ success: true }`
  - **调用方**: AI Agent Service (任务开始时)。

- **`rpc CompleteTaskWithPostcard (CompleteTaskRequest) returns (CompleteTaskResponse)`**
  - **描述**: AI Agent 完成工作后，调用此接口。它将一次性完成两件事：1) 创建 `Postcards` 记录；2) 更新 `Tasks` 表的状态为 `COMPLETED`。这是一个**事务性操作 (`@Transactional`)**，必须保证原子性。
  - **请求**: `{ task_id: "...", postcard_data: { user_id: 123, frontend_code: "...", ... } }`
  - **响应**: `{ postcard_id: 456 }`
  - **调用方**: AI Agent Service (任务成功时)。

- **`rpc FailTask (FailTaskRequest) returns (FailTaskResponse)`**
  - **描述**: AI Agent 任务失败时调用，用于更新任务状态。
  - **请求**: `{ task_id: "...", error_message: "..." }`
  - **响应**: `{ success: true }`
  - **调用方**: AI Agent Service (任务失败时)。

- **`rpc GetTaskStatus (GetTaskStatusRequest) returns (GetTaskStatusResponse)`**
  - **描述**: 供 API 网关轮询查询任务状态。
  - **请求**: `{ task_id: "..." }`
  - **响应**: `{ status: "COMPLETED", data: { ...postcard_details... } }` 或 `{ status: "PROCESSING" }`
  - **调用方**: API 网关。

- **`rpc GetPostcardById (GetPostcardRequest) returns (PostcardResponse)`**
- **`rpc ListPostcardsByUser (ListPostcardsRequest) returns (ListPostcardsResponse)`**

## 4. 技术选型

- **框架**: Spring Boot
- **数据库**: PostgreSQL (推荐，因其强大的 JSONB 支持)
- **ORM**: Spring Data JPA
- **服务间通信**: gRPC 或 REST 