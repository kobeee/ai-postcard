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
- **先设计后开发**：不急于写代码，按研发流程推进
- 设计应包含测试case，先写测试代码验证需求理解

**通用开发原则**：
- **可测试性**：编写可测试代码，组件保持单一职责
- **DRY 原则**：避免重复代码，提取共用逻辑
- **代码简洁**：遵循 KISS 原则
- **命名规范**：使用描述性变量、函数和类名
- **注释文档**：为复杂逻辑添加注释
- **风格一致**：遵循项目风格指南
- **利用生态**：优先使用成熟库和工具
- **架构设计**：考虑可维护性、可扩展性和性能
- **版本控制**：编写有意义的提交信息
- **异常处理**：正确处理边缘情况和错误
- **响应语言**：始终使用中文回复用户

#### 开发工作流自动化规则 (development-workflow.mdc)

**自动化容器管理**：
- 开发和测试必须在容器化环境中进行
- 测试时自动使用 `docker-compose` 启动服务及依赖
- 示例：测试 `user-service` 时运行 `sh scripts/dev.sh up user`

**依赖变更管理**：
- 新增 Python 依赖必须通过重建 Docker 镜像更新
- 工作流：主机修改 `requirements.txt` → `docker-compose build <service>` → 重启服务
- 代码热更新只针对源代码文件

**环境资源管理**：
- 任务完成后**必须**自动关闭 Docker 容器：`sh scripts/dev.sh down`
- 长时间不活跃容器应自动停止
- 开始新任务前检查并清理之前环境

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

**文档要求**：
- 所有文档使用 Markdown 格式，使用中文
- 使用 `CHANGELOG.md` 记录开发历史，以追加方式更新
- 结构脉络清晰，记录完整上下文和思考过程
- 代码示例应完整可运行，添加适当注释

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
- 遵循 PEP 8 风格指南
- 使用类型注解增强代码可读性
- 使用虚拟环境管理依赖（`venv` 或 `poetry`）
- 使用上下文管理器处理资源
- 优先使用列表推导式、生成器表达式
- 使用 `pytest` 进行测试，保持高测试覆盖率
- 使用 `dataclasses` 或 `pydantic` 模型表示数据
- **测试代码必须存放到相应的 tests 目录下**

#### FastAPI 开发规范 (fastapi.mdc)

**最佳实践**：
- 为所有函数参数和返回值使用类型提示
- 使用 Pydantic 模型进行请求和响应验证
- 在路径操作装饰器中使用适当的 HTTP 方法
- 使用依赖注入实现共享逻辑
- 使用后台任务进行非阻塞操作
- 使用适当的状态码进行响应
- 使用 APIRouter 按功能组织路由

#### Vue.js 开发规范 (vuejs.mdc)

**组件开发**：
- 使用组合式 API 而非选项式 API
- 保持组件小巧且专注
- 正确集成 TypeScript
- 实现适当的 props 验证
- 使用正确的 emit 声明
- 保持模板逻辑简洁

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