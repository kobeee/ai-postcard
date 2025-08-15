"""
AI Agent Service - AI明信片项目的核心AI服务
包含AI代码生成、明信片创作等功能
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import logging
import logging.config
from datetime import datetime
from dotenv import load_dotenv

# 导入编码服务API
from .coding_service.api import router as coding_router
from .coding_service.config import settings

# 加载环境变量
load_dotenv()

# 配置日志系统
def setup_logging():
    """配置详细的日志系统"""
    # 创建日志目录
    log_dir = "/app/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志文件路径
    log_file = os.path.join(log_dir, f"ai-agent-service-{datetime.now().strftime('%Y-%m-%d')}.log")
    
    # 日志配置
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            '': {  # root logger
                'level': 'DEBUG',
                'handlers': ['console', 'file']
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO', 
                'handlers': ['console', 'file'],
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Log file: {log_file}")
    logger.info(f"AI Agent Service starting up at {datetime.now()}")
    return logger

# 初始化日志系统
main_logger = setup_logging()

app = FastAPI(
    title="AI Agent Service",
    description="AI 明信片项目 - AI Agent 服务",
    version="1.0.0"
)

# 集成编码服务API路由
app.include_router(
    coding_router,
    prefix="/api/v1/coding",
    tags=["AI代码生成"]
)

# 添加静态文件服务，用于托管前端应用
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 添加lovart.ai模拟器的根路由
@app.get("/lovart-sim")
async def lovart_simulator():
    """重定向到lovart.ai模拟器页面"""
    from fastapi.responses import FileResponse
    static_file = os.path.join(static_dir, "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    else:
        return {"error": "前端文件未找到"}

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
        "features": [
            "AI代码生成 (lovart.ai模拟器)",
            "实时代码预览",
            "多AI模型支持"
        ],
        "endpoints": [
            "/",
            "/health", 
            "/info",
            "/docs",
            "/lovart-sim",  # lovart.ai模拟器入口
            "/api/v1/coding/generate-code",
            "/api/v1/coding/status/{task_id}",
            "/api/v1/coding/tasks/{task_id}/status"
        ],
        "websocket_endpoints": [
            "/api/v1/coding/status/{task_id}"
        ],
        "ai_provider": settings.AI_PROVIDER_TYPE,
        "default_model": settings.CLAUDE_DEFAULT_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
