"""
AI Agent Service - 最小化 FastAPI 应用
用于环境验证和基础服务测试
"""
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="AI Agent Service",
    description="AI 明信片项目 - AI Agent 服务",
    version="1.0.0"
)

class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str

@app.get("/")
async def root():
    """根路径 - 基础健康检查"""
    return {
        "message": "AI Agent Service is running",
        "service": "ai-agent-service",
        "status": "healthy"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """详细健康检查"""
    return HealthResponse(
        status="healthy",
        service="ai-agent-service",
        environment=os.getenv("APP_ENV", "development")
    )

@app.get("/info")
async def service_info():
    """服务信息"""
    return {
        "service": "ai-agent-service",
        "version": "1.0.0",
        "description": "AI 明信片生成服务",
        "endpoints": [
            "/",
            "/health",
            "/info",
            "/docs"  # FastAPI 自动生成的文档
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
