# API 规范 (V1)

## 1. 概述

本文档是 "AI 明信片" 项目前后端通信的官方契约。所有 API 都通过 API 网关暴露，并以 `https://api.yourdomain.com/v1` 作为基地址。

### 1.1. 通用约定

- **数据格式**: 所有请求和响应体都使用 `application/json` 格式。
- **认证**: 除登录接口外，所有需要授权的 API 都必须在 HTTP 请求头中包含 `Authorization: Bearer <jwt_token>`。
- **错误处理**: 服务端发生错误时，响应体应包含一个标准的错误对象：
  ```json
  {
    "error_code": "RESOURCE_NOT_FOUND",
    "message": "指定的明信片不存在"
  }
  ```

## 2. API 端点详述

### 2.1. 用户认证模块 (`/users`)

#### `POST /users/login`

- **描述**: 客户端使用从微信获取的 `code` 进行登录或注册，换取会话 `token`。
- **请求体**:
  ```json
  {
    "code": "0a3b1c2d..."
  }
  ```
- **成功响应 (200 OK)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_info": {
        "user_id": 123,
        "nickname": "张三",
        "avatar_url": "https://..."
    },
    "is_new_user": false
  }
  ```
- **失败响应 (400 Bad Request)**:
  ```json
  {
    "error_code": "INVALID_CODE",
    "message": "微信 code 无效或已过期"
  }
  ```
- **路由至**: `user-service`

### 2.2. 明信片模块 (`/postcards`)

#### `POST /postcards/create`

- **描述**: 发起一个异步的明信片创建任务。
- **认证**: 需要 `Authorization` 头。
- **请求体** (参考 `prd/ai-postcard-prd-v2.md` 的输入参数):
  ```json
  {
    "mood": "激动",
    "style": "梵高",
    "theme": "庆祝胜利",
    "context": {
      "location": "上海",
      "weather": "晴"
    }
  }
  ```
- **成功响应 (202 Accepted)**: 表明服务器已接受请求并正在处理。
  ```json
  {
    "task_id": "e4a5f8c1-b3d2-4c9a-8e7f-6d5a4b3c2d1e"
  }
  ```
- **后端交互**: 消息发布到消息队列。

#### `GET /postcards/status/{taskId}`

- **描述**: 轮询查询指定异步任务的当前状态。
- **认证**: 需要 `Authorization` 头。
- **路径参数**: `taskId` (string, required) - `create` 接口返回的任务 ID。
- **成功响应 (200 OK)**:
  - **处理中**:
    ```json
    { "status": "PROCESSING" }
    ```
  - **失败**:
    ```json
    {
      "status": "FAILED",
      "error": {
        "error_code": "AI_GENERATION_FAILED",
        "message": "图像生成模型调用超时"
      }
    }
    ```
  - **成功**:
    ```json
    {
      "status": "COMPLETED",
      "data": {
        "postcard_id": 456,
        "frontend_code": "<html>...</html>",
        "image_url": "https://...",
        "copywriting_text": "...",
        "created_at": "2023-10-27T10:00:00Z"
      }
    }
    ```
- **失败响应 (404 Not Found)**:
    ```json
    {
        "error_code": "TASK_NOT_FOUND",
        "message": "指定的任务ID不存在"
    }
    ```
- **路由至**: `postcard-service`

#### `GET /postcards/me`

- **描述**: 获取当前登录用户的个人作品集（已生成的明信片列表）。
- **认证**: 需要 `Authorization` 头。
- **查询参数**:
    - `page` (integer, optional, default: 1): 页码。
    - `size` (integer, optional, default: 10): 每页数量。
- **成功响应 (200 OK)**:
  ```json
  {
    "total": 25,
    "page": 1,
    "size": 10,
    "items": [
      {
        "postcard_id": 456,
        "thumbnail_url": "https://.../thumbnail.jpg", // 可能是 image_url 的缩略图版本
        "created_at": "2023-10-27T10:00:00Z"
      }
    ]
  }
  ```
- **路由至**: `postcard-service` 