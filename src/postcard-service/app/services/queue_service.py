import os
import json
import logging
import redis.asyncio as redis
from typing import Dict, Any
from ..models.task import PostcardGenerationTask

logger = logging.getLogger(__name__)

class QueueService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_password = os.getenv("REDIS_PASSWORD", "redis")
        self.stream_name = os.getenv("QUEUE_STREAM_NAME", "postcard_tasks")
        self.consumer_group = os.getenv("QUEUE_CONSUMER_GROUP", "ai_agent_workers")
        self._redis_client = None

    async def get_redis_client(self):
        """获取Redis客户端"""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    password=self.redis_password,
                    decode_responses=True
                )
                # 测试连接
                await self._redis_client.ping()
                logger.info("✅ Redis连接成功")
            except Exception as e:
                logger.error(f"❌ Redis连接失败: {e}")
                raise
        return self._redis_client

    async def publish_task(self, task: PostcardGenerationTask):
        """发布任务到消息队列"""
        try:
            client = await self.get_redis_client()
            
            # 将任务序列化为字典
            task_data = task.dict()
            
            # 发布到Redis Stream
            message_id = await client.xadd(self.stream_name, task_data)
            
            logger.info(f"✅ 任务发布成功: {task.task_id} - 消息ID: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"❌ 发布任务失败: {task.task_id} - {e}")
            raise

    async def create_consumer_group(self):
        """创建消费者组（如果不存在）"""
        try:
            client = await self.get_redis_client()
            
            try:
                await client.xgroup_create(
                    self.stream_name, 
                    self.consumer_group, 
                    id="0", 
                    mkstream=True
                )
                logger.info(f"✅ 消费者组创建成功: {self.consumer_group}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"✅ 消费者组已存在: {self.consumer_group}")
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"❌ 创建消费者组失败: {e}")
            raise

    async def close(self):
        """关闭Redis连接"""
        if self._redis_client:
            await self._redis_client.close()
            logger.info("✅ Redis连接已关闭")