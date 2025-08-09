# 设计文档 10: 容器化与本地开发环境

> **文档状态**: 第三版
> **负责人**: AI 架构师
> **更新日期**: 2024-08-03

## 1. 概述与目标

为了确保开发、测试和生产环境的一致性，消除“在我机器上可以运行”的问题，并提升团队协作效率，本项目的所有后端服务都将采用容器化技术进行管理。本文档详细阐述了本地开发环境的容器化方案设计。

**核心目标:**

- **环境一致性**: 使用 Docker 确保所有环境（开发、测试、生产）的运行时高度一致。
- **服务隔离**: 每个服务在独立的容器中运行，拥有独立的依赖和配置，互不干扰。
- **按需启动**: 开发者通过单个脚本即可快速启动或停止所需的部分或完整的后端服务环境。
- **开发效率**: 支持代码热加载（Hot Reload），开发者修改代码后无需手动重启服务。
- **场景化支持**: 为单个服务提供多种启动模式（如正常运行、运行测试、执行脚本），以适应复杂的开发需求。

## 2. 整体容器化架构

我们将使用 `Docker` 对所有后端服务及依赖的中间件进行容器化，并利用 `Docker Compose` 在本地进行统一的服务编排和管理。

### 2.1. 架构图

```mermaid
graph TD
    subgraph "Developer Machine (localhost)"
        subgraph "Docker Environment (Managed by Docker Compose)"
            direction LR
            
            subgraph "Application Services"
                A["gateway-service"]
                U["user-service"]
                P["postcard-service"]
                AI["ai-agent-service"]
            end
            
            subgraph "Infrastructure Services"
                DB["fa:fa-database postgres-db"]
                Cache["fa:fa-server redis-cache"]
            end

            A -- "Routes to" --> U
            A -- "Routes to" --> P
            A -- "Routes to" --> AI

            U -- "Uses" --> DB
            P -- "Uses" --> DB
            AI -- "Uses" --> DB

            U -- "Uses" --> Cache
            P -- "Uses" --> Cache
        end

        W["WeChat DevTools"]
        
        W -- "API Requests via localhost:port" --> A
    end

    style W fill:#dff,stroke:#333,stroke-width:2px
```

## 3. 各服务容器化设计 (Dockerfile 蓝图)

每个服务目录下都会有一个 `Dockerfile` 文件，用于定义如何构建其 Docker 镜像。设计保持不变。

## 4. 本地开发环境编排 (Docker Compose 设计)

项目根目录的 `docker-compose.yml` 文件是本地开发环境的“总开关”。

### 4.1. `docker-compose.yml` 核心结构
(基础结构保持不变，将在后续章节中通过 Profiles 和扩展进行增强)

### 4.2. 环境配置 (`.env`)
- 在项目根目录创建 `.env` 文件，用于存放数据库密码、API 密钥等敏感信息。
- 提供 `.env.example` 文件作为模板，指導开发者配置必要环境。

## 5. 聚焦单服务的开发工作流

### 5.1. 挑战：提升“内循环”开发效率
当开发者在单个服务（如 `user-service`）中开发某个功能时，启动包含所有微服务的完整后端技术栈通常是不必要的。

### 5.2. 解决方案：使用 Docker Compose Profiles
我们采用 Docker Compose 的 `profiles` 功能来应对这一挑战。`profiles` 允许我们为服务打上标签，然后根据标签选择性地启动一组服务。

### 5.3. `docker-compose.yml` Profiles 设计

```yaml
# version: '3.8'

services:
  # --- 基础设施服务 (无 profile) ---
  postgres-db:
    # ...
  redis-cache:
    # ...

  # --- 应用服务 (每个都有独立的 profile) ---
  gateway-service:
    build: ./src/gateway-service
    profiles: ["gateway"]
    ports: ["8080:8080"]

  user-service:
    build: ./src/user-service
    profiles: ["user"]
    ports: ["8081:8080"]
    depends_on: [postgres-db, redis-cache]
```
(其他服务定义类似)

## 6. 统一启动与管理脚本

我们引入一个功能强大的统一管理脚本：`scripts/dev.sh`。

### 6.1. 核心功能
- **启动服务**: `sh scripts/dev.sh up <profile1> <profile2> ...`
- **停止服务**: `sh scripts/dev.sh down`
- **查看日志**: `sh scripts/dev.sh logs <service_name>`
- **重启服务**: `sh scripts/dev.sh restart <service_name>`

### 6.2. 聚焦开发工作流示例
**场景**: 开发者需要为 `user-service` 添加一个新的 API，并希望通过 `gateway-service` 进行测试。
1.  **启动相关服务**:
    ```bash
    sh scripts/dev.sh up gateway user
    ```
2.  **编码与测试**: 修改代码，通过 `http://localhost:8080` 进行测试。
3.  **关闭环境**:
    ```bash
    sh scripts/dev.sh down
    ```

---

## 7. 场景化服务启动：满足更细粒度的开发需求

### 7.1. 挑战：单一启动模式的局限性
在实际开发中，我们不仅需要启动一个服务，还希望以**不同的模式**启动它。例如，针对 `AI Agent` 服务，我们可能面临以下场景：
- **场景 A (默认)**: 启动 `uvicorn` Web 服务器，以接收来自网关的真实请求。
- **场景 B (测试)**: 在容器内运行 `pytest` 测试套件，以确保测试环境与部署环境完全一致。
- **场景 C (脚本执行)**: 运行一个一次性的维护脚本（如数据迁移、缓存预热），这个脚本需要访问服务的所有依赖（如数据库）。

如果只为 `ai-agent-service` 定义一个启动配置，开发者将不得不在不同场景间手动修改 `docker-compose.yml` 的 `command`，这非常低效且容易出错。

### 7.2. 解决方案：YAML 锚点与服务扩展
为了实现场景化启动，我们将结合使用 Docker Compose 的 `profiles` 和 YAML 的 **锚点（Anchor, `&`）** 与 **扩展（Extension, `<<`）** 特性。

1.  **定义基础服务**: 我们使用 YAML 锚点 (`&`) 为一个服务定义一个可复用的“基础配置块”。这个配置块包含 `build`, `volumes`, `environment`, `depends_on` 等所有场景共享的配置。为了避免被 Docker Compose 识别为可独立启动的服务，我们使用 `x-` 前缀，这是 YAML 的一个约定。
2.  **定义场景化变体**: 我们定义多个“虚拟”服务，每个服务代表一种启动场景。它们通过扩展语法 (`<<:`) 继承基础配置，并各自覆盖 `command` 并指定一个唯一的 `profile`。

### 7.3. `docker-compose.yml` 场景化设计示例
以下是 `ai-agent-service` 应用此模式后的 `docker-compose.yml` 设计：

```yaml
# version: '3.8'

services:
  # ... (postgres, redis, gateway, user, postcard 服务定义) ...

  # 使用 'x-' 前缀和锚点 '&' 定义一个不可直接运行的、可复用的基础配置
  x-ai-agent-base: &ai-agent-base
    build: ./src/ai-agent-service
    volumes:
      - ./src/ai-agent-service:/app
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres-db:5432/${DB_NAME}
      # ... 其他通用环境变量 ...
    depends_on:
      - postgres-db
      - redis-cache
      - postcard-service

  # --- AI Agent 服务的场景化变体 ---

  # 场景 1: 默认运行模式
  ai-agent-service:
    <<: *ai-agent-base  # 继承基础配置
    profiles:
      - "agent"         # 定义 profile 为 'agent'
    ports:
      - "8001:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # 场景 2: 运行测试套件
  ai-agent-service-tests:
    <<: *ai-agent-base  # 继承基础配置
    profiles:
      - "agent-tests"   # 定义 profile 为 'agent-tests'
    command: pytest -v

  # 场景 3: 运行一次性脚本
  ai-agent-service-script:
    <<: *ai-agent-base  # 继承基础配置
    profiles:
      - "agent-script"  # 定义 profile 为 'agent-script'
    # 允许通过环境变量动态传入要执行的命令
    command: sh -c "${SCRIPT_COMMAND:-echo 'No command provided. Exiting.'}"
```

### 7.4. 场景化工作流示例

通过 `dev.sh` 脚本，开发者现在可以精确地启动他们需要的任何场景：

- **启动 `agent` 服务的默认 Web 服务模式**:
  ```bash
  sh scripts/dev.sh up agent
  ```
  *(Docker Compose 会查找 `profile: "agent"` 的服务并启动它)*

- **在容器内运行 `agent` 服务的测试套件**:
  ```bash
  sh scripts/dev.sh up agent-tests
  ```
  *(这将启动 `ai-agent-service-tests` 及其依赖，执行 `pytest` 后容器会自动退出)*

- **在 `agent` 服务的环境中执行一个数据清理脚本**:
  ```bash
  export SCRIPT_COMMAND="python scripts/cleanup_data.py"
  sh scripts/dev.sh up agent-script
  ```
  *(开发者通过设置环境变量 `SCRIPT_COMMAND` 来指定要运行的命令)*

通过这种设计，我们极大地增强了本地开发环境的灵活性和能力，使其能够优雅地处理从简单到复杂的各种开发与测试场景，而无需对核心配置文件进行任何修改。

---

## 8. 深入优化开发体验：依赖持久化与代码热更新

### 8.1 问题背景：开发循环中的摩擦

在 `第 7 节` 中，我们设计了灵活的场景化启动模式。然而，在日常的编码-测试-调试的“内循环”中，开发者还面临两大挑战：
1.  **依赖持久化**：当为服务添加新的第三方库时，如果直接在容器内安装（如 `docker exec <container> pip install new_package`），这些新增的依赖会随着容器的停止而丢失。开发者必须频繁重建镜像（`docker-compose up --build`），严重拖慢了开发节奏。
2.  **代码同步与热更新**：虽然 `uvicorn --reload` 等工具提供了基础的热更新，但我们需要一个覆盖所有技术栈的、统一的策略，确保代码修改能被即时同步到容器内并触发服务自动重启，而无需手动操作。

### 8.2 核心策略：主机与容器双向同步

我们的解决方案核心是**将源代码目录和依赖目录从开发主机（Host）挂载到容器（Container）中**。

```mermaid
graph TD
    subgraph "Developer's Host Machine"
        direction LR
        HostSrc["Source Code<br/>(e.g., ./src/user-service)"]
        HostDeps["Dependency Folder<br/>(e.g., .venv, node_modules)"]
    end

    subgraph "Docker Container"
        direction LR
        ContainerSrc["/app"]
        ContainerDeps["/app/.venv or /app/node_modules"]
    end

    HostSrc -- "Volume Mount" --> ContainerSrc
    HostDeps -- "Volume Mount" --> ContainerDeps
    
    ContainerSrc -- "Watched by" --> HotReloadTool["Hot Reload Tool<br/>(nodemon, uvicorn --reload)"]
    HotReloadTool -- "Restarts" --> AppProcess["Application Process"]
    
    style HostSrc fill:#e6f3ff,stroke:#333
    style HostDeps fill:#e6f3ff,stroke:#333
```

这一策略带来了两大好处：
- **依赖在主机侧管理**：开发者在自己的主机上使用熟悉的工具（如 `pip`, `npm`）管理依赖。所做的更改（安装、卸载库）会保存在主机的文件系统中，并通过挂载实时同步到容器里。依赖关系不再因容器生命周期而丢失。
- **源码即时生效**：主机上的任何代码变更都会通过挂载立即反映在容器的文件系统中，这使得容器内的热更新工具能够监测到变化并自动重新加载应用。

### 8.3 各技术栈实施指南

我们将此策略应用到不同服务中。以下是针对常见技术栈的 `docker-compose.yml` 配置蓝图和工作流程。

#### 8.3.1 Python 服务 (如 `ai-agent-service`)

以 `ai-agent-service` 为例，我们采用本地虚拟环境（`venv`）的方案。

- **工作流**:
    1.  **主机端**: 在 `src/ai-agent-service/` 目录下创建并激活虚拟环境：
        ```bash
        # In ./src/ai-agent-service/
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        ```
    2.  **添加新依赖**: `pip install <new-package>` 并更新 `requirements.txt` (`pip freeze > requirements.txt`)。这些变更都发生在主机的 `.venv` 和 `requirements.txt` 文件中。
    3.  **容器端**: 容器启动后，会直接使用挂载进来的、包含所有依赖的 `.venv` 环境。

- **`docker-compose.yml` 配置**:
    ```yaml
    # In docker-compose.yml
    x-ai-agent-base: &ai-agent-base
      build:
        context: ./src/ai-agent-service
        dockerfile: Dockerfile.dev # 使用专为开发优化的 Dockerfile
      volumes:
        # 挂载整个服务目录，包括源代码和 .venv
        - ./src/ai-agent-service:/app
      environment:
        # 确保容器内的 Python 知道使用虚拟环境
        - PATH="/app/.venv/bin:$PATH"
        - PYTHONPATH=/app
      # ... (其他配置)

    ai-agent-service:
      <<: *ai-agent-base
      profiles: ["agent"]
      ports: ["8001:8000"]
      command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

- **`Dockerfile.dev` 示例**:
    ```dockerfile
    FROM python:3.10-slim
    WORKDIR /app
    # 开发镜像只需设置工作目录和暴露端口即可
    # 所有依赖和源码都通过挂载卷提供
    # CMD 在 docker-compose.yml 中定义
    ```

- **`Dockerfile` (生产环境)**:
    ```dockerfile
    FROM python:3.10-slim
    WORKDIR /app
    # 生产镜像则需要完整复制虚拟环境和代码
    COPY requirements.txt .
    RUN python3 -m venv .venv && . .venv/bin/activate && pip install --no-cache-dir -r requirements.txt
    COPY . .
    # 设置路径以便直接使用 venv 中的可执行文件
    ENV PATH="/app/.venv/bin:$PATH"
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

#### 8.3.2 Node.js 服务 (如 `gateway-service`)

对于 Node.js 服务，我们直接挂载包含 `node_modules` 的整个项目目录。

- **工作流**:
    1.  **主机端**: 在 `src/gateway-service/` 目录下安装依赖：
        ```bash
        # In ./src/gateway-service/
        npm install
        ```
    2.  **添加新依赖**: `npm install <new-package> --save`。`node_modules` 和 `package.json` 会在主机上更新。
    3.  **容器端**: 容器通过挂载直接使用主机的 `node_modules`。

- **`docker-compose.yml` 配置**:
    ```yaml
    # In docker-compose.yml
    gateway-service:
      build:
        context: ./src/gateway-service
        dockerfile: Dockerfile.dev
      profiles: ["gateway"]
      ports: ["8080:8080"]
      volumes:
        # 挂载整个服务目录，包括源代码和 node_modules
        - ./src/gateway-service:/app
        # 匿名卷，解决主机与容器 node_modules 权限和二进制不兼容问题
        # - /app/node_modules
      command: npm run dev # 假设 package.json 中定义了 "dev": "nodemon index.js"
    ```
    *注：如果遇到 macOS/Windows 与 Linux 容器之间 `node_modules` 中二进制文件不兼容的问题，可采用上述注释掉的匿名卷技巧。但这会使容器内的 `npm install` 结果与主机不同步。在团队成员都使用类 Unix 系统（macOS/Linux）时，直接挂载通常更简单。我们将首先采用直接挂载的方式。*

- **`Dockerfile.dev` 示例**:
    ```dockerfile
    FROM node:18-alpine
    WORKDIR /app
    # 开发镜像仅复制 package.json，以备容器内需要手动重装依赖
    COPY package*.json ./
    # 依赖和源码通过挂载卷提供
    CMD ["npm", "run", "dev"]
    ```

#### 8.3.3 Go 服务

Go Modules 机制让依赖管理更为优雅。我们可以将模块缓存目录挂载到容器中，以加速依赖下载。

- **工作流**: 开发者在主机上正常编写代码，`go mod tidy` 等命令会自动管理依赖。

- **`docker-compose.yml` 配置**:
    ```yaml
    # In docker-compose.yml
    some-go-service:
      build: ./src/some-go-service
      profiles: ["go-service"]
      volumes:
        # 挂载源代码
        - ./src/some-go-service:/app
        # 将主机的 Go 模块缓存挂载到容器中，避免重复下载
        - go-mod-cache:/go/pkg/mod
      command: air -c .air.toml # 使用 air 工具实现热重载

    volumes:
      go-mod-cache: # 定义一个具名卷
    ```

### 8.4 更新后的 `dev.sh` 脚本和工作流

此设计对 `dev.sh` 脚本功能**没有影响**。开发者依然使用 `sh scripts/dev.sh up <profile>` 来启动服务。最大的改变在于工作流本身：

- **旧工作流**: 改代码 -> （可能）改 Dockerfile -> 重建镜像 `sh scripts/dev.sh up --build` -> 测试
- **新工作流**:
    - **改代码**: 保存文件，服务自动热更新。
    - **加依赖**: 在主机上 `pip/npm install` -> （可能）保存代码 -> 服务自动热更新。

这一改进将极大地提升“内循环”开发效率，使开发者能更专注于业务逻辑的实现，而非环境配置。