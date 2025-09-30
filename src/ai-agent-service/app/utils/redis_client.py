"""
Redis Client 单例管理器
提供同步Redis连接供签体曝光追踪器使用
"""

import redis
import os
import logging

logger = logging.getLogger(__name__)

_redis_client = None

def get_redis_client():
    """获取Redis客户端单例（同步版本）"""
    global _redis_client

    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            redis_password = os.getenv("REDIS_PASSWORD", "redis")

            # 解析URL
            if redis_url.startswith("redis://"):
                # 格式: redis://host:port
                host_port = redis_url.replace("redis://", "")
                if ":" in host_port:
                    host, port = host_port.split(":")
                    port = int(port)
                else:
                    host = host_port
                    port = 6379
            else:
                host = "redis"
                port = 6379

            _redis_client = redis.Redis(
                host=host,
                port=port,
                password=redis_password,
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=False  # 保持bytes格式，由tracker自行处理
            )

            # 测试连接
            _redis_client.ping()
            logger.info(f"✅ Redis同步客户端初始化成功: {host}:{port}")

        except Exception as e:
            logger.error(f"❌ Redis同步客户端初始化失败: {e}")
            _redis_client = None
            raise

    return _redis_client

def close_redis_client():
    """关闭Redis连接（优雅退出时调用）"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("✅ Redis连接已关闭")