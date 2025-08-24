from fastapi import FastAPI
import os
import logging
from logging.handlers import RotatingFileHandler

app = FastAPI(
    title="User Service", 
    description="用户认证服务，处理微信小程序登录和用户管理",
    version="1.0.0"
)

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
