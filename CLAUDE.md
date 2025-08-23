# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在该代码仓库中工作时提供指导。

## 项目概述

这是一个基于微服务架构的 AI 明信片生成系统。核心创新在于 AI 不仅生成内容，更是充当"前端工程师"，编写可交互、带动画的 HTML/CSS/JS 代码，生成在微信小程序 web-view 中渲染的动态明信片。

## 系统架构

**微服务结构：**
- `src/gateway-service/` - API 网关 (Node.js/Express)
- `src/user-service/` - 用户管理 (Python/FastAPI)
- `src/postcard-service/` - 明信片数据管理 (Python/FastAPI)  
- `src/ai-agent-service/` - **核心 AI Agent** (Python/FastAPI) 包含编排器和工具集
- 基础设施：PostgreSQL + Redis + Docker Compose

**AI Agent 工作流程：**
1. 文本生成（概念/文案）
2. 图片生成  
3. **前端代码生成**（带动画的 HTML/CSS/JS）
4. 返回完整的动态明信片代码

## 开发命令

### 环境搭建
```bash
# 初始化环境
sh scripts/setup-dev-env.sh
cp .env.example .env
# 编辑 .env 配置文件
sh scripts/validate-env.sh
```

### 服务管理（主要方式）
使用统一的开发脚本进行所有操作：

```bash
# 启动服务
sh scripts/dev.sh up gateway user          # API 网关 + 用户服务
sh scripts/dev.sh up agent                 # AI Agent 服务
sh scripts/dev.sh up postcard             # 明信片服务
sh scripts/dev.sh up all                  # 所有服务

# 查看服务状态和日志
sh scripts/dev.sh ps                      # 服务状态
sh scripts/dev.sh logs                    # 所有日志
sh scripts/dev.sh logs ai-agent-service   # 特定服务日志

# 停止服务
sh scripts/dev.sh down

# 在容器中执行命令
sh scripts/dev.sh exec ai-agent-service bash
sh scripts/dev.sh exec postgres psql -U postgres -d ai_postcard

# 清理环境
sh scripts/dev.sh clean                   # 删除所有容器/卷
```

### 测试
```bash
# 运行服务测试
sh scripts/dev.sh up ai-agent-tests       # AI Agent 测试
sh scripts/dev.sh up user-tests          # 用户服务测试
sh scripts/dev.sh up postcard-tests      # 明信片服务测试

# 在 ai-agent-service 中运行 Python 测试
sh scripts/dev.sh exec ai-agent-service pytest
sh scripts/dev.sh exec ai-agent-service pytest tests/test_claude_provider.py -v
```

### 前端开发（AI Agent 服务）
AI Agent 服务包含用于测试的 Vue.js 前端：

```bash
# 在 ai-agent-service 容器内
cd app/frontend
npm run dev                              # 开发服务器
npm run build                           # 生产构建
```

### 直接使用 Docker Compose（备选方式）
```bash
# 基于 profile 的服务管理
docker-compose --profile agent up -d    # 仅 AI Agent
docker-compose --profile gateway up -d  # 仅网关
docker-compose --profile all up -d      # 所有服务
```

## 配置说明

### 必需的环境变量
- `DB_PASSWORD` - PostgreSQL 密码
- `REDIS_PASSWORD` - Redis 密码  
- `APP_SECRET` - 应用密钥
- `ANTHROPIC_AUTH_TOKEN` - Claude API 密钥（AI Agent 使用）
- `AI_PROVIDER_TYPE=claude` - AI 提供商选择

### 关键配置文件
- `.env` - 环境变量（从 `.env.example` 复制）
- `docker-compose.yml` - 包含 profiles 的服务定义
- `src/ai-agent-service/requirements.txt` - Python 依赖
- `src/gateway-service/package.json` - Node.js 依赖

## AI Agent 服务详情

**核心 Provider 系统：**
- 位于 `src/ai-agent-service/app/coding_service/`
- `providers/claude_provider.py` - 主要 Claude 集成
- `providers/factory.py` - Provider 选择逻辑
- 使用 `claude-code-sdk==0.0.20` 实现 AI 编码能力

**测试策略：**
- `tests/test_claude_provider.py` - Provider 单元测试
- `tests/test_sdk_smoke.py` - SDK 集成测试
- 在 Docker 容器内运行测试以确保一致性

## 数据库架构

**主要表：**
- `users` - 用户资料，集成微信
- `postcards` - 生成的明信片，`frontend_code` 字段存储 AI 生成的 HTML/CSS/JS

## 重要提醒

- **AI Agent 是核心** - 开发重点关注 `src/ai-agent-service/`
- 所有服务使用开发 Dockerfile (`Dockerfile.dev`) 支持热重载
- 前端代码生成是关键差异化功能 - AI 编写完整的交互式网页
- 所有开发任务使用 `scripts/dev.sh` 包装脚本
- 启动前务必用 `sh scripts/validate-env.sh` 验证环境
- 项目使用 Docker profiles 实现选择性服务启动

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