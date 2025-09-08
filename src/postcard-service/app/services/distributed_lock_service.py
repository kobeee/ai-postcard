# -*- coding: utf-8 -*-
"""
分布式锁服务
实现Redis分布式锁和并发控制机制
"""

import os
import time
import socket
import asyncio
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DistributedLockService:
    """分布式锁服务"""
    
    def __init__(self, redis_client=None):
        if redis_client:
            self.redis = redis_client
        else:
            # 创建Redis连接
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.from_url(redis_url, decode_responses=True)
        
        self.lock_timeout = 30  # 30秒超时
        self.retry_delay = 0.1  # 100ms
        self.max_retry = 3  # 最大重试次数
        self.instance_id = f"{socket.gethostname()}_{os.getpid()}"
        
        logger.info(f"🔒 分布式锁服务初始化: instance_id={self.instance_id}")
    
    async def acquire_quota_lock(self, user_id: str, operation: str = "CREATE") -> Optional[str]:
        """获取配额操作分布式锁"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        lock_value = f"{self.instance_id}:{int(time.time())}"
        
        try:
            # 使用SET命令的NX和EX参数实现原子锁
            acquired = await self.redis.set(
                lock_key, 
                lock_value, 
                ex=self.lock_timeout,
                nx=True
            )
            
            if acquired:
                logger.debug(f"🔐 获得配额锁: {lock_key} by {self.instance_id}")
                return lock_value
            else:
                logger.warning(f"⏰ 配额锁获取失败: {lock_key}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取配额锁异常: {str(e)}")
            return None
    
    async def acquire_lock_with_retry(self, user_id: str, operation: str = "CREATE") -> Optional[str]:
        """带重试的分布式锁获取"""
        for attempt in range(self.max_retry):
            lock_value = await self.acquire_quota_lock(user_id, operation)
            if lock_value:
                return lock_value
            
            if attempt < self.max_retry - 1:
                # 指数退避策略
                delay = self.retry_delay * (2 ** attempt)
                logger.debug(f"⏱️ 锁获取重试 {attempt + 1}/{self.max_retry}, 延迟 {delay}s")
                await asyncio.sleep(delay)
        
        logger.warning(f"⚠️ 分布式锁获取失败，已重试 {self.max_retry} 次: {user_id}:{operation}")
        return None
    
    async def release_quota_lock(self, user_id: str, operation: str, lock_value: str) -> bool:
        """释放配额操作分布式锁"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        
        try:
            # 🔥 使用Lua脚本确保原子释放
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, lock_key, lock_value)
            if result:
                logger.debug(f"🔓 释放配额锁: {lock_key}")
                return True
            else:
                logger.warning(f"⚠️ 配额锁释放失败: {lock_key} - 可能已过期或被其他实例持有")
                return False
                
        except Exception as e:
            logger.error(f"❌ 释放配额锁异常: {str(e)}")
            return False
    
    async def extend_lock(self, user_id: str, operation: str, lock_value: str, extend_time: int = 30) -> bool:
        """延长锁的持有时间"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        
        try:
            # Lua脚本：检查锁是否属于当前实例，然后延长时间
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("EXPIRE", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, lock_key, lock_value, extend_time)
            if result:
                logger.debug(f"⏰ 锁时间延长: {lock_key}, 延长 {extend_time}s")
                return True
            else:
                logger.warning(f"⚠️ 锁时间延长失败: {lock_key}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 延长锁时间异常: {str(e)}")
            return False
    
    @asynccontextmanager
    async def quota_lock_context(self, user_id: str, operation: str = "CREATE"):
        """配额锁上下文管理器"""
        lock_value = await self.acquire_lock_with_retry(user_id, operation)
        
        if not lock_value:
            raise Exception("无法获取分布式锁，请稍后重试")
        
        try:
            yield lock_value
        finally:
            await self.release_quota_lock(user_id, operation, lock_value)
    
    async def is_locked(self, user_id: str, operation: str = "CREATE") -> bool:
        """检查是否已被锁定"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        try:
            result = await self.redis.get(lock_key)
            return result is not None
        except Exception as e:
            logger.error(f"❌ 检查锁状态异常: {str(e)}")
            return False
    
    async def get_lock_info(self, user_id: str, operation: str = "CREATE") -> Optional[Dict[str, Any]]:
        """获取锁信息"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        try:
            lock_value = await self.redis.get(lock_key)
            if lock_value:
                # 解析锁值
                parts = lock_value.split(":")
                if len(parts) >= 2:
                    instance = ":".join(parts[:-1])
                    timestamp = int(parts[-1])
                    
                    # 获取TTL
                    ttl = await self.redis.ttl(lock_key)
                    
                    return {
                        "locked": True,
                        "instance_id": instance,
                        "locked_at": timestamp,
                        "ttl": ttl,
                        "lock_key": lock_key
                    }
            
            return {"locked": False}
            
        except Exception as e:
            logger.error(f"❌ 获取锁信息异常: {str(e)}")
            return {"locked": False, "error": str(e)}
    
    async def force_unlock(self, user_id: str, operation: str = "CREATE") -> bool:
        """强制解锁（管理员功能）"""
        lock_key = f"quota_lock:{user_id}:{operation}"
        try:
            result = await self.redis.delete(lock_key)
            if result:
                logger.warning(f"🔓 强制解锁: {lock_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 强制解锁异常: {str(e)}")
            return False
    
    async def cleanup_expired_locks(self) -> int:
        """清理过期锁（维护任务）"""
        try:
            pattern = "quota_lock:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            expired_count = 0
            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # 没有过期时间的锁
                    await self.redis.delete(key)
                    expired_count += 1
                    logger.info(f"🧹 清理无过期时间的锁: {key}")
            
            logger.info(f"🧹 锁清理完成，清理了 {expired_count} 个过期锁")
            return expired_count
            
        except Exception as e:
            logger.error(f"❌ 清理过期锁异常: {str(e)}")
            return 0


class QuotaLockError(Exception):
    """配额锁异常"""
    pass


class ConcurrentUpdateError(Exception):
    """并发更新异常"""
    pass


# 全局分布式锁服务实例
_lock_service = None

async def get_lock_service() -> DistributedLockService:
    """获取分布式锁服务实例"""
    global _lock_service
    if _lock_service is None:
        _lock_service = DistributedLockService()
    return _lock_service