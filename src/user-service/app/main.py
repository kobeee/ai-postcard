from fastapi import FastAPI
import os
import logging
from logging.handlers import RotatingFileHandler

# 🔥 导入安全中间件
from .middleware.auth_middleware import AuthenticationMiddleware
from .middleware.api_security_middleware import APISecurityMiddleware
from .middleware.audit_monitoring_middleware import AuditMonitoringMiddleware

app = FastAPI(
    title="User Service", 
    description="🔐 AI明信片用户认证服务 - 企业级安全架构",
    version="2.0.0"
)

# 🔥 添加安全中间件（注意顺序：审计监控->API安全检查->JWT认证）
app.add_middleware(AuditMonitoringMiddleware)
app.add_middleware(APISecurityMiddleware)
app.add_middleware(AuthenticationMiddleware)

# 日志配置
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(log_dir, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = RotatingFileHandler(os.path.join(log_dir, 'user-service.log'), maxBytes=10*1024*1024, backupCount=5)
fh.setFormatter(fmt)
fh.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(fh)

@app.get("/")
async def read_root():
    return {"message": "用户服务运行正常"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# 包含API路由
from .api import miniprogram

# 注册小程序API路由
app.include_router(miniprogram.router, prefix="/api/v1")
