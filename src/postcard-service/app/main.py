import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from .database.connection import init_database
from .services.queue_service import QueueService
from .api.postcards import router as postcards_router

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    logger.info("🚀 启动 Postcard Service")
    
    # 初始化数据库
    try:
        init_database()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise
    
    # 初始化消息队列
    try:
        queue_service = QueueService()
        await queue_service.create_consumer_group()
        logger.info("✅ 消息队列初始化完成")
    except Exception as e:
        logger.error(f"❌ 消息队列初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("🔄 关闭 Postcard Service")
    await queue_service.close()

app = FastAPI(
    title="Postcard Service",
    description="AI明信片生成任务管理服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    postcards_router,
    prefix="/api/v1/postcards",
    tags=["明信片任务"]
)

@app.get("/")
async def read_root():
    return {
        "message": "AI明信片任务管理服务",
        "service": "postcard-service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "postcard-service",
        "environment": os.getenv("APP_ENV", "development")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
