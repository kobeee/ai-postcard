from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from typing import Any, Dict

app = FastAPI(
    title="Gateway Service",
    description="AI明信片项目API网关，支持微信小程序",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志配置
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(log_dir, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = RotatingFileHandler(os.path.join(log_dir, 'gateway-service.log'), maxBytes=10*1024*1024, backupCount=5)
fh.setFormatter(fmt)
fh.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(fh)

logger = logging.getLogger(__name__)

# 服务URL配置
SERVICES = {
    "user-service": os.getenv("USER_SERVICE_URL", "http://user-service:8000"),
    "postcard-service": os.getenv("POSTCARD_SERVICE_URL", "http://postcard-service:8000"), 
    "ai-agent-service": os.getenv("AI_AGENT_SERVICE_URL", "http://ai-agent-service:8000")
}

@app.get("/")
async def read_root():
    return {
        "message": "AI明信片项目网关服务",
        "status": "运行正常",
        "version": "1.0.0",
        "services": SERVICES
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gateway-service", 
        "version": "1.0.0"
    }

# 代理请求的通用函数
async def proxy_request(
    target_url: str,
    method: str,
    path: str,
    request: Request,
    timeout: int = 30
) -> Dict[Any, Any]:
    """代理HTTP请求到目标服务"""
    try:
        # 构建完整URL
        full_url = f"{target_url}{path}"
        
        # 准备请求头
        headers = dict(request.headers)
        headers.pop("host", None)  # 移除原始host头
        headers["X-Client-Type"] = "miniprogram"
        headers["X-Forwarded-For"] = request.client.host
        
        # 获取请求体
        body = None
        if method.upper() in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # 发起请求
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=full_url,
                params=dict(request.query_params),
                headers=headers,
                content=body
            )
            
            logger.info(f"代理请求: {method} {full_url} -> {response.status_code}")
            
            # 返回响应
            try:
                return response.json()
            except:
                return {"code": 0, "message": "成功", "data": response.text}
                
    except httpx.TimeoutException:
        logger.error(f"请求超时: {target_url}{path}")
        return {"code": -1, "message": "服务请求超时", "data": None}
    except Exception as e:
        logger.error(f"代理请求失败: {str(e)}")
        return {"code": -1, "message": f"服务暂时不可用: {str(e)}", "data": None}

# 小程序用户认证路由
@app.api_route("/api/v1/miniprogram/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_auth_proxy(path: str, request: Request):
    """小程序认证服务代理"""
    return await proxy_request(
        SERVICES["user-service"],
        request.method,
        f"/api/v1/miniprogram/auth/{path}",
        request
    )

# 小程序明信片服务路由  
@app.api_route("/api/v1/miniprogram/postcards/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_postcards_proxy(path: str, request: Request):
    """小程序明信片服务代理"""
    return await proxy_request(
        SERVICES["postcard-service"],
        request.method,
        f"/api/v1/miniprogram/postcards/{path}",
        request
    )

# 小程序AI生成服务路由
@app.api_route("/api/v1/miniprogram/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def miniprogram_ai_proxy(path: str, request: Request):
    """小程序AI服务代理"""
    return await proxy_request(
        SERVICES["ai-agent-service"],
        request.method,
        f"/api/v1/miniprogram/ai/{path}",
        request,
        timeout=120  # AI服务需要更长超时时间
    )

# 小程序健康检查
@app.get("/api/v1/miniprogram/health")
async def miniprogram_health():
    """小程序API健康检查"""
    return {
        "code": 0,
        "message": "小程序API网关正常运行",
        "data": {
            "services": SERVICES,
            "status": "healthy"
        }
    }

# 小程序版本信息
@app.get("/api/v1/miniprogram/version")
async def miniprogram_version():
    """小程序API版本信息"""
    return {
        "code": 0,
        "message": "版本信息获取成功",
        "data": {
            "version": "1.0.0",
            "features": [
                "微信登录认证",
                "情绪罗盘卡片生成",
                "AI明信片创作",
                "作品管理",
                "分享功能"
            ]
        }
    }
