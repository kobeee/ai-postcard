# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在该代码仓库中工作时提供指导。

## 前置小tips
**对于内容过大的文本文件，采用分批次读取的方式**
**严格控制每个代码文件的代码数量，及时拆分，避免单个文件过大**

## 项目概述

“AI 心象签”项目通过 AI 工作流在微信小程序中生成挂件式求签体验：用户在小程序内绘制情绪墨迹、回答心境问答，系统触发异步任务完成概念、文案、图像与结构化内容生成，最终展示可翻面的传统挂件与解签笺。微服务后端、Redis Streams 队列和丰富的资源配置共同支撑整套体验。

## 系统架构

- `src/gateway-service/` —— API 网关（FastAPI），统一处理小程序到后端的请求与转发。
- `src/user-service/` —— 用户与认证服务（FastAPI），实现微信登录、JWT/RBAC、安全审计等能力。
- `src/postcard-service/` —— 心象签任务与结果服务（FastAPI），负责配额、任务状态、结构化数据扁平化及持久化。
- `src/ai-agent-service/` —— AI Agent（FastAPI + Worker），消费 Redis Stream 任务、执行 AI 编排并挂载静态资源。
- 基础设施：PostgreSQL（`data/postgres`）+ Redis（`data/redis`）+ Docker Compose profiles；静态签体与题库位于 `resources/` 并通过 AI Agent 的 `/resources` 路径向外暴露。

系统围绕 Redis Stream `postcard_tasks` 解耦请求提交与 AI 生成，Worker 与服务均通过 `.env` 中的 `INTERNAL_SERVICE_TOKEN` 做内部鉴权。

## AI Agent 工作流程

工作流在 `PostcardWorkflow` 中定义，核心步骤如下：
1. **ConceptGenerator**：结合墨迹分析、问答洞察与环境信息生成自然意象，并通过 `charm-config.json` 选择 18 款签体之一（多路径 fallback）。
2. **ContentGenerator**：生成祝福语、笔触解读、生活指引等文案。
3. **ImageGenerator**：调用 Gemini/META 图片通道，若缺失则提供占位图并记录元数据。
4. **StructuredContentGenerator**：输出心象签结构化数据（含 `charm_identity`、`oracle_manifest`、`ai_selected_charm` 等），并写入背景图 URL。所有步骤配有兜底/回退策略。

执行完成后通过 `postcard-service` 的状态接口写入概念、文案、图片、结构化数据，失败时自动回滚配额并落盘错误信息。

## 环境初始化与服务管理

统一脚本为 `./scripts/run.sh`，支持容器构建、依赖准备与权限修复。

```bash
cp .env.example .env                 # 按需调整密钥/配置
./scripts/run.sh init                # 初始化数据库 / Redis / 队列
./scripts/run.sh up all              # 构建并启动全部服务
./scripts/run.sh up gateway user     # 按 profile 启动指定服务
./scripts/run.sh ps                  # 查看容器状态
./scripts/run.sh logs ai-agent-service -f   # 跟踪某服务日志
./scripts/run.sh exec postgres psql -U postgres -d ai_postcard   # 进入容器
./scripts/run.sh down                # 停止并清理网络
./scripts/run.sh clean              # （确认后）删除容器与数据卷
./scripts/run.sh clean-user-data    # 仅清理业务数据，保留系统配置
```

所有 profile 定义见 `docker-compose.yml`，包括 `all/gateway/user/postcard/agent/worker` 以及对应的测试 profile。

## 测试与验证

默认策略是记录验证步骤而非强制执行，但需要测试时请使用对应 profile：

```bash
./scripts/run.sh up agent-tests         # 运行 AI Agent 测试容器
./scripts/run.sh up user-tests          # 运行用户服务测试容器
./scripts/run.sh up postcard-tests      # 运行明信片服务测试容器
```

如需临时在容器内执行额外 pytest，可使用 `./scripts/run.sh exec ai-agent-service pytest ...`。验证记录与手动测试流程请归档至 `docs/tests/validation/`（最新记录：`2025-09-24-heart-oracle-comprehensive-fixes.md`）。

## 配置要点

- `.env` 为统一入口，关键变量包括数据库/缓存凭证（`DB_*`, `REDIS_*`）、内部通信密钥（`INTERNAL_SERVICE_TOKEN`）、JWT/RBAC 配置、AI Provider 选择（`AI_PROVIDER_TYPE`）、Claude 与 Gemini/META 的 API Key 及模型参数。
- 静态资源：`resources/签体/` 存放 18 款签体 PNG 与 `charm-config.json`；`resources/题库/question.json` 提供心境速测题库。
- 日志与持久化目录需可写（脚本会在 Linux/macOS 下自动调整权限）。

## 数据与队列

- PostgreSQL 关键表：`users`（微信用户信息与安全属性）、`postcards`（任务状态、中间结果、`structured_data` JSON、扁平化字段）。
- Redis：`postcard_tasks` Stream + `ai_agent_workers` 消费者组用于任务编排；脚本会在初始化和数据清理时确保其存在。
- 删除业务数据时务必保留 Stream 与消费者组，遵循 `scripts/run.sh clean-user-data` 内的安全路径。

## 关键参考文档

- `docs/design/00-system-architecture.md` —— 最新系统架构与异步流程说明。
- `docs/design/10-containerization-and-dev-environment.md` —— 容器化与本地开发策略。
- `docs/design/19-hanging-charm-experience.md` —— 挂件体验视觉与交互规范。
- `CHANGELOG.md` —— 版本迭代、核心修复与优化记录。
- `docs/tests/validation/2025-09-24-heart-oracle-comprehensive-fixes.md` —— 最近一次全链路验证报告。

# 🔧 测试需知 (重要)

**快速测试和调试的关键指南，必须熟练掌握这些方法以提高开发效率。**

## 🔐 认证系统和Token获取

### 登录体系架构
- **微信小程序登录流程**: `code` → `session_key` + `openid` → JWT Token
- **登录接口**: `POST /api/v1/miniprogram/auth/login`
- **Token类型**: 
  - `access_token`: 用于API请求认证 (Bearer Token)
  - `refresh_token`: 用于刷新access_token

### 快速获取测试Token
```bash
# 1. 使用测试用户登录获取token
curl -X POST "http://localhost:8081/api/v1/miniprogram/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "test_code_for_development", 
    "userInfo": {
      "nickName": "测试用户",
      "avatarUrl": "https://example.com/avatar.jpg",
      "gender": 1
    }
  }'

# 2. 从响应中提取token字段（注意：字段名是"token"而非"access_token"）
# 响应格式: {"code": 0, "data": {"token": "eyJ...", "refreshToken": "..."}}

# 3. 后续API请求使用Bearer Token格式
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8083/api/v1/miniprogram/postcards/result/<task_id>"
```

### ⚠️ 认证常见问题和解决方案
```bash
# 问题1: 401认证失败 - 字段名错误
# ❌ 错误：使用 "access_token" 字段
TOKEN=$(curl ... | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['access_token'])")

# ✅ 正确：使用 "token" 字段  
TOKEN=$(curl ... | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")

# 问题2: 401认证失败 - Bearer格式错误
# ❌ 错误：缺少Bearer前缀
curl -H "Authorization: $TOKEN" "http://localhost:8083/..."

# ✅ 正确：使用Bearer前缀
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8083/..."

# 问题3: 验证Token有效性
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8081/api/v1/miniprogram/users/me"

# 问题4: 重新获取Token（如果过期）
TOKEN=$(curl -s -X POST "http://localhost:8081/api/v1/miniprogram/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code_for_development", "userInfo": {"nickName": "测试用户"}}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")
```

### 网关路由说明
- **用户服务**: `localhost:8081` (直接访问)
- **其他服务**: `localhost:8083` (通过网关访问)
- **API Gateway路由**:
  - `/api/v1/miniprogram/auth/*` → user-service
  - `/api/v1/miniprogram/postcards/*` → postcard-service
  - `/api/v1/environment/*` → ai-agent-service

## ⚡ 快速测试方法

### 容器内文件热更新 (推荐)
**无需重建镜像，直接拷贝修改的文件到容器内进行快速测试：**

```bash
# Python服务快速更新流程
# 1. 修改源码文件
nano src/postcard-service/app/api/miniprogram.py

# 2. 拷贝到容器内对应路径
docker cp src/postcard-service/app/api/miniprogram.py \
  ai-postcard-postcard-service:/app/app/api/miniprogram.py

# 3. 重启服务容器 (uvicorn会自动重载)
./scripts/run.sh restart postcard-service

# 4. 立即测试修改效果
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8083/api/v1/miniprogram/postcards/result/<task_id>"
```

### 常用快速拷贝命令
```bash
# PostCard Service
docker cp src/postcard-service/app/api/miniprogram.py \
  ai-postcard-postcard-service:/app/app/api/miniprogram.py

docker cp src/postcard-service/app/services/postcard_service.py \
  ai-postcard-postcard-service:/app/app/services/postcard_service.py

# AI Agent Service  
docker cp src/ai-agent-service/app/orchestrator/steps/structured_content_generator.py \
  ai-postcard-ai-agent-service:/app/app/orchestrator/steps/structured_content_generator.py

# User Service
docker cp src/user-service/app/api/miniprogram.py \
  ai-postcard-user-service:/app/app/api/miniprogram.py
```

### 服务重启命令
```bash
# 单个服务重启 (推荐)
./scripts/run.sh restart postcard-service
./scripts/run.sh restart ai-agent-service
./scripts/run.sh restart user-service

# 批量重启
./scripts/run.sh restart postcard-service ai-agent-service
```

## 📊 调试和监控

### 实时日志查看
```bash
# 查看特定服务日志
./scripts/run.sh logs postcard-service -f
./scripts/run.sh logs ai-agent-worker -f

# 查看最近50行日志
./scripts/run.sh logs postcard-service -n 50

# 多服务日志并行查看
./scripts/run.sh logs postcard-service ai-agent-service -f
```

### 数据库快速查询
```bash
# 进入PostgreSQL
./scripts/run.sh exec postgres psql -U postgres -d ai_postcard

# 常用查询
SELECT id, status, created_at FROM postcards ORDER BY created_at DESC LIMIT 5;
SELECT structured_data::json->'ai_selected_charm' FROM postcards WHERE id='<task_id>';
```

### 容器内执行命令
```bash
# 进入容器调试
./scripts/run.sh exec postcard-service bash
./scripts/run.sh exec ai-agent-service python -c "import json; print('test')"

# 直接执行Python脚本测试
docker exec ai-postcard-postcard-service python -c "
from app.api.miniprogram import flatten_structured_data
data = {'ai_selected_charm': {'charm_id': 'test'}}
result = flatten_structured_data(data)
print('✅ 扁平化测试:', result.get('ai_selected_charm_id'))
"
```

## 🎯 完整测试流程示例

### 端到端API测试流程
```bash
# ✅ 正确的完整测试流程
# 1. 获取登录Token（注意使用正确的字段名"token"）
TOKEN=$(curl -s -X POST "http://localhost:8081/api/v1/miniprogram/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code_for_development", "userInfo": {"nickName": "测试用户"}}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")

# 验证Token获取成功
echo "获取的Token: $TOKEN"

# 2. 创建心象签任务（包含完整的测试数据）
TASK_ID=$(curl -s -X POST "http://localhost:8083/api/v1/miniprogram/postcards/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "今天心情很平静，想要感受内心的宁静", 
    "style": "heart-oracle", 
    "theme": "心象意境",
    "questions": [
      {"question": "你最近的心境如何？", "answer": "内心很平和"},
      {"question": "你希望得到什么指引？", "answer": "希望保持内心的宁静"}
    ]
  }' | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['task_id'])")

echo "创建的任务ID: $TASK_ID"

# 3. 检查任务状态
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8083/api/v1/miniprogram/postcards/status/$TASK_ID"

# 4. 监控AI Agent处理日志（可选）
# ./scripts/run.sh logs ai-agent-worker -f

# 5. 等待任务完成后获取结果
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8083/api/v1/miniprogram/postcards/result/$TASK_ID" | \
  python3 -c "
import json,sys
data = json.load(sys.stdin)['data']
print('✅ 统一内容生成器测试结果:')
print(f'  状态: {data.get(\"status\", \"未找到\")}')
print(f'  AI选择的签体: {data.get(\"ai_selected_charm_id\", \"未找到\")}')
print(f'  签名: {data.get(\"charm_name\", \"未找到\")}') 
print(f'  祝福语: {data.get(\"oracle_affirmation\", \"未找到\")}')
print(f'  背景图片: {data.get(\"background_image_url\", \"未找到\")}')
"
```

### 🔥 统一内容生成器工作流验证
```bash
# 验证2025-09-28优化后的4步工作流
# 1. 检查工作流版本配置
grep "WORKFLOW_VERSION" .env

# 2. 验证日志中的步骤进度（应显示1/4到4/4）
./scripts/run.sh logs ai-agent-worker -n 20 | grep "步骤"

# 3. 验证统一内容生成器的输出结构
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8083/api/v1/miniprogram/postcards/result/$TASK_ID" | \
  python3 -c "
import json,sys
data = json.load(sys.stdin)['data']
structured_data = data.get('structured_data', {})
print('🔥 统一内容生成器字段验证:')
key_fields = ['oracle_theme', 'charm_identity', 'ai_selected_charm', 'oracle_manifest', 'visual']
for field in key_fields:
    status = '✅' if field in structured_data else '❌'
    print(f'  {status} {field}')
print(f'生成的字段总数: {len(structured_data)}')
"
```

### 关键测试检查点
1. **Token有效性**: 确保登录响应包含`access_token`
2. **任务创建**: 确保返回有效的`task_id`
3. **AI处理**: 检查`ai-agent-worker`日志无错误
4. **数据扁平化**: 验证结果包含`ai_selected_charm_id`等关键字段
5. **小程序数据**: 确认所有`oracle_*`字段正确传输

## 🚨 常见问题快速解决

### 401认证失败
```bash
# 🔍 诊断步骤1: 检查Token是否正确获取
echo "当前Token: $TOKEN"
if [ -z "$TOKEN" ]; then
  echo "❌ Token为空，需要重新获取"
else
  echo "✅ Token已获取"
fi

# 🔍 诊断步骤2: 验证Token格式和有效性
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8081/api/v1/miniprogram/users/me"

# 🔧 解决方案1: 重新获取Token（使用正确的字段名）
TOKEN=$(curl -s -X POST "http://localhost:8081/api/v1/miniprogram/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code_for_development", "userInfo": {"nickName": "测试用户"}}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['data']['token'])")

# 🔧 解决方案2: 检查API响应格式
curl -s -X POST "http://localhost:8081/api/v1/miniprogram/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code_for_development", "userInfo": {"nickName": "测试用户"}}' | \
  python3 -c "import json,sys; data=json.load(sys.stdin); print('字段名:', list(data['data'].keys()))"

# 🔧 解决方案3: 确保使用Bearer前缀
# ❌ 错误示例: curl -H "Authorization: $TOKEN"
# ✅ 正确示例: curl -H "Authorization: Bearer $TOKEN"
```

### 🚨 Token常见错误对照表
```
错误代码          | 原因                    | 解决方案
401认证失败       | 使用了access_token字段   | 改用token字段
401认证失败       | 缺少Bearer前缀          | 添加"Bearer "前缀  
Token为空        | JSON解析字段名错误       | 检查响应结构使用正确字段
-401缺少身份验证令牌| 完全没有Authorization头  | 添加完整的Authorization头
```

### 服务连接失败
```bash
# 检查服务状态
./scripts/run.sh ps
./scripts/run.sh logs gateway-service -n 20

# 重启问题服务
./scripts/run.sh restart <service-name>
```

### AI Agent处理异常
```bash
# 检查Worker健康状态
./scripts/run.sh logs ai-agent-worker -n 50

# 检查Redis队列状态
./scripts/run.sh exec redis redis-cli XLEN postcard_tasks
```

---

## 重要提醒

- AI Agent 服务与 Worker 依赖 `/resources` 挂载，请保证签体配置与 PNG 同步更新。
- 所有敏感密钥应在 `.env` 中替换示例值，切勿提交真实凭证。
- 提交异步任务前需确保 `postcard-service` 和 `ai-agent-worker` 均已运行，否则请求会一直处于排队状态。
- 任何环境清理前请备份数据目录 (`data/`、`logs/`) 以及 `resources/` 中的新增素材。
- README 的"快速开始"章节与本文件保持一致，遇到差异请优先更新这两处文档。

## 项目开发规则和规范

> **重要提醒**：以下规则至关重要，是项目开发必须遵守的核心规范，确保代码质量、开发效率和团队协作的一致性。

### 基础开发规范

#### 核心开发原则 (core.mdc)

**研发流程**：
- 接需求→写PRD→需求分析→系统设计和分析→测试设计和分析→研发→测试
- **先设计后开发**：接到每个需求，不要着急写代码，按照研发流程一步步推进
- 设计应该包含测试case，先将测试代码写好验证需求理解
- 实际开发过程中，应该先将测试代码写好，因为测试就是验证既定的输入可以得到预期的结果

**通用开发原则**：
- **可测试性**：编写可测试代码，组件保持单一职责
- **DRY 原则**：避免重复代码，提取共用逻辑到单独的函数或类
- **代码简洁**：保持代码简洁明了，遵循 KISS 原则（保持简单直接）
- **命名规范**：使用描述性的变量、函数和类名，反映其用途和含义
- **注释文档**：为复杂逻辑添加注释
- **风格一致**：遵循项目或语言的官方风格指南和代码约定
- **利用生态**：优先使用成熟的库和工具，避免不必要的自定义实现
- **架构设计**：考虑代码的可维护性、可扩展性和性能需求
- **版本控制**：编写有意义的提交信息，保持逻辑相关的更改在同一提交中
- **异常处理**：正确处理边缘情况和错误，提供有用的错误信息
- **代码行数**：如果单个文件的代码函数过长了，就应该重构拆分，避免文件代码行数过长，导致难以理解
- **响应语言**：始终使用中文回复用户

#### 开发工作流自动化规则 (development-workflow.mdc)

**自动化容器管理**：
- 开发和测试活动必须在与 `docs/design/10-containerization-and-dev-environment.md` 设计一致的容器化环境中进行
- 测试时必须自动使用 `docker-compose` 和相应的 `profile` 启动该服务及其所有依赖项
- 示例：测试 `user-service` 时运行 `sh scripts/dev.sh up user`

**自动化构建流程**：
- 在修改任何服务的源代码后，必须自动触发该服务的依赖安装和 Docker 镜像的重新构建
- 通常通过 `docker-compose up --build` 或 `sh scripts/dev.sh up <profile> --build` 来实现

**依赖变更自动感知与更新**：
- **核心原则**：新增的 Python 依赖必须通过重建 Docker 镜像来更新到运行环境中，以确保环境的绝对一致性
- **Python 服务依赖更新工作流**:
  1. 开发者在主机上修改对应服务的 `requirements.txt` 文件
  2. 开发者必须运行 `docker-compose build <service-name>` 来重新构建服务的镜像
  3. 重新启动服务 (`sh scripts/dev.sh up <profile>`)
- 代码热更新只针对源代码文件

**自动化测试与构建环境**：
- **默认策略（重要）**：开发完成后，**默认不执行测试验证操作**
- 测试相关的代码、容器入口与脚本仍须存在并保持可用
- 将测试验证步骤**单独文档化**，保存到 `docs/tests/validation/` 下，以便需要时手动执行验证
- **按需执行测试（可选）**：需要执行测试时，仍必须通过容器运行：`sh scripts/dev.sh up <service>-tests`
- **热重载与实时同步**：源代码的修改通过卷挂载实现实时同步，容器内的 `uvicorn --reload` 会自动检测源代码变化并重新加载服务

**环境资源管理**：
- **任务完成后自动清理**：开发任务、测试任务完成后，**必须**自动关闭相关的 Docker 容器
- **智能资源管理**：长时间不活跃的容器应自动停止，保留数据卷，只停止运行中的容器
- **环境状态检查**：在开始新任务前，检查并清理之前的环境

**Redis数据清理安全规则**：
- **🚨 重要警告**：在清理Redis缓存时，必须避免删除以下关键基础配置数据：
  - `postcard_tasks` - Redis Stream任务队列，删除后会导致消费者组无法工作
  - `ai_agent_workers` - 消费者组配置，删除后任务消费会完全失效
  - 其他以`QUEUE_`开头的环境变量定义的Stream和Group名称
- **安全清理命令**：使用模式匹配清理缓存，避免误删基础设施数据
  ```bash
  # ✅ 安全的缓存清理（仅清理临时缓存数据）
  redis-cli --scan --pattern "cache:*" | xargs redis-cli DEL
  redis-cli --scan --pattern "session:*" | xargs redis-cli DEL
  redis-cli --scan --pattern "temp:*" | xargs redis-cli DEL
  
  # ❌ 危险操作 - 切勿执行
  redis-cli FLUSHALL  # 会删除所有数据，包括Stream和消费者组
  redis-cli FLUSHDB   # 会删除当前数据库的所有数据
  ```
- **恢复机制**：系统已增强容错能力，当检测到Stream或消费者组丢失时会自动重建，但仍应避免不当清理

#### 环境变量管理 (env-management.mdc)

**核心原则**：
- `env.example`：版本控制中的模板文件，包含所有环境变量
- `.env`：本地实际配置文件，包含敏感信息，已被gitignore

**AI 助手协作流程**：
1. 新增环境变量时必须先更新 `env.example`
2. 明确提醒用户同步更新本地 `.env` 文件
3. 假定用户已更新配置后继续操作

#### 项目结构规范 (project-structure.mdc)

**目录组织原则**：
- 所有服务源码位于 `src/`
- 项目级测试位于 `tests/`，各模块内部可有独立 `tests/`
- 每个服务包含：`app/`（源码）、`tests/`、`scripts/`、`README.md`
- **测试代码路径约束**：测试文件必须存放在各自模块的 `tests/` 目录下

#### 文档规范 (document.mdc)

**通用要求**：
- 所有文档使用 Markdown 格式，使用中文作为主要语言
- 使用简洁、清晰的语言，文档内容应保持最新
- 避免拼写和语法错误

**目录结构**：
- `docs/` 存放详细文档
  - `guide/` 使用指南
  - `api/` API文档
  - `examples/` 示例代码文档
  - `prd/` 需求prd文档
  - `design/` 设计文档
  - `ideas/` 创意文档
  - `tests/` 测试与验证文档根目录
    - `validation/` 验证步骤文档（将测试验证操作转为文档化记录）

**开发记录规范**：
- 使用 `CHANGELOG.md` 记录每次开发的内容，包括做了什么事情、加了什么功能、修复了什么问题、改了哪些文件和代码等等
- **📝 必须在CHANGELOG.md文件的末尾新增开发记录**：所有开发更新都必须追加到文件末尾，保持时间顺序
- **每次都以换行追加到末尾的方式，即最末尾的为最新的更新记录**
- 结构脉络清晰，可以区分模块功能，切勿像记流水账一样，要完整记录上下文背景和思考过程

**验证文档规范（新增）**：
- 路径：`docs/tests/validation/`
- 命名建议：`YYYY-MM-DD-<主题>.md`
- 内容要素：环境准备/启动/关闭、日志查看位置（文件与容器）、测试用例触发方式（curl/脚本）、预期结果与判定标准、常见问题与排查
- 原则：**默认不执行测试验证操作**；仅将验证步骤文档化，必要时按文档手动执行

**代码示例规范**：
- 提供完整可运行的示例，代码应当简洁且易于理解
- 添加适当的注释解释关键部分，说明代码的预期输出或行为

#### Mermaid 图表语法规则 (mermaid-syntax.mdc)

**关键规则**：
- 所有文本（中文、空格、标点符号）必须用双引号包裹
- `end` 关键字独占一行
- 跨子图连接必须在 `subgraph` 外部定义
- 顶层 `graph` 不需要 `end` 结尾
- 避免在节点文本中使用反引号、HTML标签等特殊字符

### 技术栈特定规范

#### Python 开发规范 (python.mdc)

**核心要求**：
- 遵循 PEP 8 风格指南和命名约定
- 使用类型注解增强代码可读性和类型安全性
- 使用虚拟环境管理依赖：优先使用 `venv` 或 `poetry` 进行环境隔离
- 使用 `requirements.txt` 或 `pyproject.toml` 记录依赖
- 使用上下文管理器处理资源（如文件操作）
- 优先使用列表推导式、生成器表达式和字典推导式
- 使用 `pytest` 进行测试，保持高测试覆盖率
- 使用文档字符串（docstrings）记录函数、类和模块
- 遵循面向对象设计原则（SOLID）
- 使用异常处理保证程序健壮性
- 使用 `dataclasses` 或 `pydantic` 模型表示数据
- **测试代码必须遵从路径要求，存放到相应的tests目录下**

#### FastAPI 开发规范 (fastapi.mdc)

**最佳实践**：
- 为所有函数参数和返回值使用类型提示
- 使用 Pydantic 模型进行请求和响应验证
- 在路径操作装饰器中使用适当的 HTTP 方法（@app.get、@app.post 等）
- 使用依赖注入实现共享逻辑，如数据库连接和身份验证
- 使用后台任务（background tasks）进行非阻塞操作
- 使用适当的状态码进行响应（201 表示创建，404 表示未找到等）
- 使用 APIRouter 按功能或资源组织路由
- 适当使用路径参数、查询参数和请求体

#### Vue.js 开发规范 (vuejs.mdc)

**组件开发**：
- 使用组合式 API 而非选项式 API
- 保持组件小巧且专注
- 正确集成 TypeScript
- 实现适当的 props 验证
- 使用正确的 emit 声明
- 保持模板逻辑简洁

**组合式 API**：
- 正确使用 ref 和 reactive
- 实现适当的生命周期钩子
- 使用 composables 实现可复用逻辑
- 保持 setup 函数整洁
- 正确使用计算属性
- 实现适当的侦听器

**状态管理**：
- 使用 Pinia 进行状态管理
- 保持 stores 模块化
- 使用适当的状态组合
- 实现适当的 actions
- 正确使用 getters
- 适当处理异步状态

**性能优化**：
- 正确使用组件懒加载
- 实现适当的缓存
- 正确使用计算属性
- 避免不必要的侦听器
- 正确使用 v-show 与 v-if
- 实现适当的 key 管理

**路由管理**：
- 正确使用 Vue Router
- 实现适当的导航守卫
- 正确使用路由元字段
- 适当处理路由参数
- 实现适当的懒加载
- 使用适当的导航方法

**表单处理**：
- 正确使用 v-model
- 实现适当的验证
- 适当处理表单提交
- 显示适当的加载状态
- 使用适当的错误处理
- 实现适当的表单重置

**TypeScript 集成**：
- 使用适当的组件类型定义
- 实现适当的 prop 类型
- 使用适当的 emit 声明
- 处理适当的类型推断
- 使用适当的 composable 类型
- 实现适当的 store 类型

**测试规范**：
- 编写适当的单元测试
- 实现适当的组件测试
- 正确使用 Vue Test Utils
- 适当测试 composables
- 实现适当的模拟
- 测试异步操作

**构建和工具**：
- 使用 Vite 进行开发
- 配置适当的构建设置
- 正确使用环境变量
- 实现适当的代码分割
- 使用适当的资源处理
- 配置适当的优化

#### TypeScript 开发规范 (typescript.mdc)

**类型系统**：
- 优先使用接口而非类型定义对象
- 避免使用 `any`，对未知类型使用 `unknown`
- 使用严格的 TypeScript 配置
- 充分利用内置工具类型
- 使用泛型实现可复用类型模式

#### CSS 和样式规范 (css.mdc)

**样式架构**：
- 组件化样式，避免全局样式污染
- 使用设计系统和主题变量保持一致性
- 移动优先的响应式设计
- 使用 Styled Components 或 CSS-in-JS
- 合理使用 Flexbox 和 CSS Grid
- 避免深层选择器嵌套（不超过3层）

### 工具和框架规范

#### Docker 容器化开发

**容器使用原则**：
- 所有业务代码运行必须在容器中进行
- 使用 `sh scripts/dev.sh` 进行统一的服务管理
- 源代码热重载通过卷挂载实现
- 依赖变更需要重建镜像
- 任务完成后必须清理容器资源

#### 微信小程序开发规范

**WXML 规范 (wxml.mdc)**：
- 使用小写标签名和属性名
- 属性值必须用双引号包围
- 数据绑定使用 `{{}}`，避免复杂逻辑
- 列表渲染必须设置 `wx:key`
- 组件标签名使用 kebab-case 格式

**WXSS 规范 (wxss.mdc)**：
- 使用 2 个空格缩进
- 类名使用 kebab-case 格式
- 优先使用 Flexbox 布局
- 使用 `rpx` 单位进行响应式设计
- 避免使用 ID 选择器和 `!important`

### 测试规范

**测试要求**：
- 单元测试覆盖率 ≥80%
- 使用描述性测试方法命名
- 遵循 Arrange-Act-Assert 模式
- 测试文件必须存放在相应的 `tests/` 目录
- 为每个公共函数编写单元测试
- 使用测试替身模拟依赖

### 安全和性能

**安全实践**：
- 正确处理输入验证
- 避免在日志中输出敏感信息
- 使用参数化查询防止 SQL 注入
- 实现适当的错误处理和异常日志
- 环境变量中存储敏感配置
- **🔒 密钥安全规则**：严禁将API密钥、Token等敏感信息打印到日志；严禁查看或访问密钥内容；仅允许验证密钥是否存在

**性能优化**：
- 避免不必要的重绘重排
- 合理使用缓存策略
- 实现懒加载和分页
- 优化数据库查询
- 使用连接池管理数据库连接

### 代码质量保证

**代码审查**：
- Pull Request 代码合并前必须审查
- 使用静态代码分析工具
- 持续重构，偿还技术债务
- 遵循 SOLID 设计原则
- 编写清晰的提交信息

这些规则构成了项目开发的核心规范体系，必须严格遵守以确保项目的质量和可维护性。
