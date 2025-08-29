import asyncio
import redis.asyncio as redis
from redis.exceptions import ResponseError
import logging
import os
import json
from typing import Dict, Any
from .models import PostcardGenerationTask
from ..orchestrator.workflow import PostcardWorkflow

logger = logging.getLogger(__name__)

class TaskConsumer:
    """任务消费者 - 从Redis Stream消费明信片生成任务"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_password = os.getenv("REDIS_PASSWORD", "redis")
        self.stream_name = os.getenv("QUEUE_STREAM_NAME", "postcard_tasks")
        self.consumer_group = os.getenv("QUEUE_CONSUMER_GROUP", "ai_agent_workers")
        self.consumer_name = f"worker_{os.getpid()}"
        
        self.redis_client = None
        self.workflow = PostcardWorkflow()
        self.running = False
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                password=self.redis_password,
                decode_responses=True
            )
            
            # 测试连接
            await self.redis_client.ping()
            self.logger.info("✅ Redis连接成功")
            
            # 确保消费者组存在
            await self.ensure_consumer_group()
            
        except Exception as e:
            self.logger.error(f"❌ Redis连接失败: {e}")
            raise
    
    async def ensure_consumer_group(self):
        """确保消费者组存在"""
        try:
            await self.redis_client.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id="0",
                mkstream=True
            )
            self.logger.info(f"✅ 消费者组创建成功: {self.consumer_group}")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                self.logger.info(f"✅ 消费者组已存在: {self.consumer_group}")
            else:
                raise
    
    async def start_consuming(self):
        """开始消费任务"""
        if not self.redis_client:
            await self.connect()
        
        self.running = True
        self.logger.info(f"🚀 开始消费任务: {self.consumer_name}")
        
        while self.running:
            try:
                # 从消费者组读取消息
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: ">"},
                    count=1,
                    block=1000  # 1秒超时
                )
                
                if messages:
                    for stream, msgs in messages:
                        for msg_id, fields in msgs:
                            await self.process_task(msg_id, fields)
                
            except asyncio.CancelledError:
                # 不让整个消费者退出，记录并继续循环，防止单次任务取消导致进程退出
                self.logger.warning("⚠️ 捕获到 CancelledError，忽略并继续监听")
                await asyncio.sleep(0.1)
                continue
            except ResponseError as e:
                # 检查是否是消费者组不存在的错误
                if "NOGROUP" in str(e):
                    self.logger.warning(f"⚠️ 消费者组不存在，尝试重新创建: {e}")
                    try:
                        await self.ensure_consumer_group()
                        self.logger.info(f"✅ 消费者组重新创建成功: {self.consumer_group}")
                        continue  # 重新尝试消费
                    except Exception as recreate_error:
                        self.logger.error(f"❌ 重新创建消费者组失败: {recreate_error}")
                        await asyncio.sleep(5)
                        continue
                else:
                    self.logger.error(f"❌ Redis ResponseError: {e}")
                    await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"❌ 消费任务失败: {e}")
                await asyncio.sleep(5)  # 错误后等待5秒
    
    async def process_task(self, msg_id: str, task_data: Dict[str, Any]):
        """处理单个任务"""
        try:
            self.logger.info(f"📨 收到任务: {msg_id}")
            
            # 解析任务数据：将可能为 JSON 字符串的字段转换为原生类型
            if "metadata" in task_data and isinstance(task_data["metadata"], str):
                try:
                    task_data["metadata"] = json.loads(task_data["metadata"]) if task_data["metadata"].strip() else {}
                except Exception:
                    task_data["metadata"] = {}

            # 构建任务模型
            task = PostcardGenerationTask(**task_data)
            self.logger.info(f"📋 任务详情: {task.task_id} - {task.user_input[:50]}...")
            
            # 执行工作流
            await self.workflow.execute(task.dict())
            
            # 确认消息处理完成
            await self.redis_client.xack(self.stream_name, self.consumer_group, msg_id)
            self.logger.info(f"✅ 任务完成: {task.task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 处理任务失败: {msg_id} - {e}")
            # 更新任务状态为失败（如果能解析到 task_id）
            try:
                task_id = task_data.get("task_id") if isinstance(task_data, dict) else None
                if task_id:
                    await self.workflow.update_task_status(task_id, "failed", str(e))
            except Exception:
                pass
            # 这里可以实现重试逻辑或死信队列
    
    async def stop_consuming(self):
        """停止消费"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        self.logger.info("🔄 消费者已停止")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            return False
        except:
            return False