#!/bin/bash

# =============================================================================
# AI 明信片项目 - 统一运维脚本（dev/prod 通用）
# =============================================================================
# 用法示例：
#   sh scripts/ops.sh init --env=dev            # 初始化（不包含应用构建/启动）
#   sh scripts/ops.sh build --env=prod          # 构建所有镜像（并行 + BuildKit）
#   sh scripts/ops.sh up all --env=prod         # 按 profile 启动（all/gateway/user/postcard/agent/worker）
#   sh scripts/ops.sh down --env=prod           # 关闭
#   sh scripts/ops.sh ps --env=dev              # 查看状态
#   sh scripts/ops.sh logs ai-agent-service     # 查看日志
#   sh scripts/ops.sh exec postgres psql -U postgres -c "\dt"   # 容器内执行
#   sh scripts/ops.sh migrate-db --env=dev      # 执行开发环境建表脚本
#   sh scripts/ops.sh health --env=prod         # 健康检查
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ENVIRONMENT="dev"   # dev|prod
BUILD_PARALLEL=true
BUILD_NO_CACHE=false

log_info(){ echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok(){ echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn(){ echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_err(){ echo -e "${RED}[ERROR]${NC} $1"; }
log_step(){ echo -e "${PURPLE}[STEP]${NC} $1"; }

usage(){
  cat <<EOF
AI 明信片项目 - 统一运维脚本

用法:
  sh scripts/ops.sh <command> [options]

命令:
  init                 初始化（创建目录、启动DB/Redis并初始化）
  build [services...]  构建镜像（默认全部服务）
  up <profiles...>     启动服务（例：all gateway user postcard agent worker）
  down                 停止服务
  ps                   查看服务状态
  logs [service]       查看日志
  exec <svc> <cmd...>  在容器中执行命令
  restart <service>     重启单个服务
  migrate-db           运行数据库建表/迁移
  health               健康检查
  help                 显示帮助

通用选项:
  --env=dev|prod       目标环境（默认 dev）
  --no-parallel        构建时禁用并行
  --no-cache           构建时禁用缓存
EOF
}

check_deps(){
  command -v docker >/dev/null || { log_err "缺少 docker"; exit 1; }
  command -v docker-compose >/dev/null || { log_err "缺少 docker-compose"; exit 1; }
}

load_env(){
  if [ -f .env ]; then
    # 以安全方式加载 .env（支持包含空格与行内注释），并自动导出
    # 依赖 bash 的 set -a / set +a 机制，避免用 export $(...) 导致 token 解析错误
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
}

declare -a DC
set_dc(){
  if [ "$ENVIRONMENT" = "prod" ]; then
    DC=(docker-compose -f docker-compose.prod.yml)
  else
    DC=(docker-compose)
  fi
}

ensure_dirs(){
  log_step "创建/权限修复目录..."
  mkdir -p ./backups \
           ./data/postgres ./data/redis ./data/ai-agent/static \
           ./logs/nginx ./logs/gateway ./logs/user ./logs/postcard ./logs/ai-agent
  chmod -R 775 ./logs ./data 2>/dev/null || true
  local uid="${APP_UID:-1000}" gid="${APP_GID:-1000}"
  chown -R "$uid":"$gid" ./logs ./data/ai-agent/static 2>/dev/null || true
}

wait_db_redis(){
  set_dc
  log_info "等待 PostgreSQL/Redis 健康..."
  sleep 5
  for i in $(seq 1 30); do
    if "${DC[@]}" exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
      log_ok "PostgreSQL 就绪"; break; fi; sleep 2; done || true
  for i in $(seq 1 30); do
    if "${DC[@]}" exec -T redis redis-cli -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1; then
      log_ok "Redis 就绪"; break; fi; sleep 2; done || true
}

cmd_init(){
  check_deps; load_env; ensure_dirs
  set_dc
  log_step "启动数据库与缓存..."
  "${DC[@]}" up -d postgres redis
  wait_db_redis
  log_step "初始化数据库结构..."
  local db="${DB_NAME:-ai_postcard}"
  if [ "$ENVIRONMENT" = "prod" ]; then
    "${DC[@]}" exec -T postgres sh -lc "psql -U postgres -d '$db' -f /docker-entrypoint-initdb.d/02-schema.sql" \
      || log_warn "生产数据库初始化可能已执行/脚本未挂载"
  else
    if [ -f scripts/init-database.sql ]; then
      "${DC[@]}" exec -T postgres sh -lc "psql -U postgres -d '$db' -f -" < scripts/init-database.sql \
        || log_warn "开发数据库初始化失败，可重试 migrate-db"
    else
      log_warn "缺少 scripts/init-database.sql，跳过初始化"
    fi
  fi
  log_step "初始化 Redis 队列..."
  "${DC[@]}" exec -T redis redis-cli -a "${REDIS_PASSWORD}" XGROUP CREATE postcard_tasks ai_agent_workers 0 MKSTREAM >/dev/null 2>&1 \
    || log_info "队列已存在"
  log_ok "初始化完成"
}

cmd_build(){
  check_deps; load_env; ensure_dirs
  export DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1
  set_dc
  local flags=(build)
  [ "$BUILD_PARALLEL" = true ] && flags+=(--parallel)
  [ "$BUILD_NO_CACHE" = true ] && flags+=(--no-cache)
  # 打印即将构建的服务列表（用于可观测性）
  log_step "解析 Compose 服务..."
  "${DC[@]}" config --services || true
  # 默认构建主要应用服务（更直观），如需覆盖可显式传参
  local default_svcs=(ai-agent-service gateway-service user-service postcard-service)
  if [ $# -gt 0 ]; then
    log_info "执行: ${DC[*]} ${flags[*]} $*"
    "${DC[@]}" "${flags[@]}" "$@"
  else
    log_info "执行: ${DC[*]} ${flags[*]} ${default_svcs[*]}"
    "${DC[@]}" "${flags[@]}" "${default_svcs[@]}"
  fi
  log_ok "构建完成"
}

cmd_up(){
  check_deps; load_env; ensure_dirs
  set_dc
  if [ $# -eq 0 ]; then
    log_err "请指定 profiles（如 all/gateway/user/postcard/agent/worker）"; exit 1
  fi
  local profiles=("$@")
  # 通过 --profile 逐个启动，兼容现有 compose 配置
  for p in "${profiles[@]}"; do
    "${DC[@]}" --profile "$p" up -d
  done
  log_ok "服务已启动"
  "${DC[@]}" ps
}

cmd_down(){ set_dc; "${DC[@]}" down; log_ok "已停止"; }
cmd_ps(){ set_dc; "${DC[@]}" ps; }
cmd_logs(){ set_dc; shift || true; "${DC[@]}" logs -f "$@"; }
cmd_exec(){ set_dc; local svc="$1"; shift; [ -z "$svc" ] && { log_err "缺少服务名"; exit 1; }; "${DC[@]}" exec "$svc" "$@"; }
cmd_restart(){ set_dc; local svc="$1"; [ -z "$svc" ] && { log_err "缺少服务名"; exit 1; }; "${DC[@]}" restart "$svc"; log_ok "已重启: $svc"; }

cmd_migrate_db(){
  check_deps; load_env
  local db
  set_dc
  db="${DB_NAME:-ai_postcard}"
  if [ -f scripts/migrate-db-schema.sql ]; then
    "${DC[@]}" exec -T postgres sh -lc "psql -U postgres -d '$db' -f -" < scripts/migrate-db-schema.sql \
      && log_ok "迁移完成" || log_warn "迁移失败"
  else
    log_warn "缺少 scripts/migrate-db-schema.sql"
  fi
}

cmd_health(){
  check_deps; load_env
  set_dc
  log_step "检查健康..."
  "${DC[@]}" ps
  for s in gateway-service user-service postcard-service ai-agent-service; do
    "${DC[@]}" exec -T "$s" curl -fsS http://localhost:8000/health >/dev/null 2>&1 && log_ok "$s: healthy" || log_warn "$s: not ready"
  done
}

# 解析全局参数（在 command 之后也可出现）
COMMAND="${1:-help}"; shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --env=*) ENVIRONMENT="${1#*=}"; shift ;;
    --no-parallel) BUILD_PARALLEL=false; shift ;;
    --no-cache) BUILD_NO_CACHE=true; shift ;;
    *) break ;;
  esac
done

case "$COMMAND" in
  init) cmd_init "$@" ;;
  build) cmd_build "$@" ;;
  up) cmd_up "$@" ;;
  down) cmd_down ;;
  ps) cmd_ps ;;
  logs) cmd_logs "$@" ;;
  exec) cmd_exec "$@" ;;
  restart) cmd_restart "$@" ;;
  migrate-db) cmd_migrate_db ;;
  health) cmd_health ;;
  help|--help|-h) usage ;;
  *) log_err "未知命令: $COMMAND"; usage; exit 1 ;;
esac
