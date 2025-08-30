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

# 导入小程序API
from .api.miniprogram import router as miniprogram_router

# 导入环境感知API
from .api.environment import router as environment_router

# 导入HTML转图片API
from .api.html_image import router as html_image_router

# 导入上传API
from .api.upload import router as upload_router

# 导入WebSearch测试服务
from .services.claude_websearch_test import ClaudeWebSearchTest

# 导入队列消费者（用于初始化）
from .queue.consumer import TaskConsumer

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

# 应用启动时的初始化函数
async def initialize_services():
    """初始化服务依赖"""
    try:
        # 初始化Redis消费者组
        consumer = TaskConsumer()
        await consumer.connect()
        await consumer.stop_consuming()  # 仅用于初始化，不开始消费
        main_logger.info("✅ Redis消费者组初始化完成")
    except Exception as e:
        main_logger.error(f"❌ 服务初始化失败: {e}")
        # 不抛出异常，让服务继续启动，Worker进程会处理这个问题

# 创建应用实例
app = FastAPI(
    title="AI Agent Service",
    description="AI 明信片项目 - AI Agent 服务",
    version="1.0.0",
    on_startup=[initialize_services]
)

# 集成编码服务API路由
app.include_router(
    coding_router,
    prefix="/api/v1/coding",
    tags=["AI代码生成"]
)

# 集成小程序API路由
app.include_router(
    miniprogram_router,
    prefix="/api/v1/miniprogram/ai",
    tags=["小程序AI服务"]
)

# 集成环境感知API路由
app.include_router(
    environment_router,
    prefix="/api/v1/environment",
    tags=["环境感知服务"]
)

# 集成HTML转图片API路由
app.include_router(
    html_image_router,
    prefix="/api/v1",
    tags=["HTML转图片服务"]
)

# 集成上传API路由
app.include_router(
    upload_router,
    prefix="/api/v1/upload",
    tags=["文件上传服务"]
)

# 初始化WebSearch测试服务
websearch_test = ClaudeWebSearchTest()

# WebSearch测试API端点
@app.get("/api/v1/test/websearch")
async def test_websearch(query: str, city: str = None):
    """测试Claude Code SDK WebSearch功能"""
    return await websearch_test.test_websearch(query, city)

@app.get("/api/v1/test/trending")  
async def test_trending_news(city: str):
    """测试热点新闻搜索功能"""
    return await websearch_test.test_trending_news(city)

# 添加静态文件服务，用于托管前端构建产物和AI生成的文件
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")

# 确保AI生成文件的static目录存在
os.makedirs(static_dir, exist_ok=True)

# 托管前端应用的根路由
@app.get("/")
async def serve_frontend():
    """托管前端应用"""
    from fastapi.responses import FileResponse
    # 前端构建后直接到static目录
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AI Agent Service is running", "service": "ai-agent-service", "status": "healthy", "note": "前端未构建，请运行: cd app/frontend && npm run build"}

# 兼容旧的lovart-sim路由
@app.get("/lovart-sim")
async def lovart_simulator():
    """Lovart.ai模拟器页面"""
    from fastapi.responses import FileResponse
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "前端文件未找到，请先构建前端: cd app/frontend && npm run build"}

# 挂载前端静态资源（CSS, JS等）
assets_dir = os.path.join(static_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    main_logger.info(f"✅ 前端资源已挂载: {assets_dir}")
else:
    main_logger.warning("前端assets目录不存在，请先构建前端")

# 挂载AI生成的文件（用于预览，需要避免与前端文件冲突）
generated_dir = os.path.join(static_dir, "generated")
os.makedirs(generated_dir, exist_ok=True)
app.mount("/generated", StaticFiles(directory=generated_dir), name="generated")
app.mount("/static/generated", StaticFiles(directory=generated_dir), name="static_generated")

# 挂载HTML转图片生成的图片文件
images_dir = os.path.join(generated_dir, "images")
os.makedirs(images_dir, exist_ok=True)
# 注意：已经包含在/generated中了，不需要单独挂载

# 创建情绪图片上传目录
emotions_dir = os.path.join(generated_dir, "emotions")
os.makedirs(emotions_dir, exist_ok=True)

# 添加根路径静态文件处理，用于AI生成的文件引用
@app.get("/script.js")
async def serve_generated_script():
    """处理AI生成页面中的script.js请求"""
    from fastapi.responses import FileResponse
    script_file = os.path.join(generated_dir, "script.js")
    if os.path.exists(script_file):
        return FileResponse(script_file, media_type="application/javascript")
    return {"error": "script.js not found"}

@app.get("/style.css")
async def serve_generated_style():
    """处理AI生成页面中的style.css请求"""
    from fastapi.responses import FileResponse
    css_file = os.path.join(generated_dir, "style.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    return {"error": "style.css not found"}

class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str

@app.get("/health-check")
async def root():
    """健康检查API"""
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
            "多AI模型支持",
            "地理位置查询 (Claude WebSearch)",
            "天气信息查询 (Claude WebSearch)",
            "热点新闻查询 (Claude WebSearch)",
            "社交媒体趋势 (Claude WebSearch)"
        ],
        "endpoints": [
            "/",
            "/health", 
            "/info",
            "/docs",
            "/lovart-sim",  # lovart.ai模拟器入口
            "/api/v1/coding/generate-code",
            "/api/v1/coding/status/{task_id}",
            "/api/v1/coding/tasks/{task_id}/status",
            "/api/v1/environment/location/reverse",  # 地理位置查询
            "/api/v1/environment/weather",  # 天气查询
            "/api/v1/environment/trending/news",  # 热点新闻
            "/api/v1/environment/trending/social",  # 社交热点
            "/api/v1/environment/trending/comprehensive",  # 综合热点
            "/api/v1/environment/complete"  # 完整环境信息
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
