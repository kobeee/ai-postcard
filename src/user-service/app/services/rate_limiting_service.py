# -*- coding: utf-8 -*-
"""
多维度限流服务
实现基于用户、IP、API端点的多层限流机制
"""

import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """限流类型"""
    USER = "user"           # 用户级限流
    IP = "ip"               # IP级限流  
    ENDPOINT = "endpoint"   # 端点级限流
    GLOBAL = "global"       # 全局限流


class RateLimitPolicy(Enum):
    """限流策略"""
    SLIDING_WINDOW = "sliding_window"     # 滑动窗口
    FIXED_WINDOW = "fixed_window"         # 固定窗口
    TOKEN_BUCKET = "token_bucket"         # 令牌桶


class RateLimitConfig:
    """限流配置"""
    
    # 默认限流规则 (requests per time_window_seconds)
    DEFAULT_LIMITS = {
        # 用户级限流
        RateLimitType.USER: {
            "create_postcard": {"limit": 5, "window": 300},      # 5次/5分钟
            "login": {"limit": 10, "window": 300},               # 10次/5分钟
            "query_quota": {"limit": 100, "window": 60},         # 100次/分钟
            "list_postcards": {"limit": 50, "window": 60},       # 50次/分钟
        },
        
        # IP级限流
        RateLimitType.IP: {
            "create_postcard": {"limit": 20, "window": 300},     # 20次/5分钟
            "login": {"limit": 50, "window": 300},               # 50次/5分钟  
            "default": {"limit": 500, "window": 60},             # 默认500次/分钟
        },
        
        # 端点级限流
        RateLimitType.ENDPOINT: {
            "create_postcard": {"limit": 100, "window": 60},     # 100次/分钟
            "login": {"limit": 200, "window": 60},               # 200次/分钟
        },
        
        # 全局限流
        RateLimitType.GLOBAL: {
            "default": {"limit": 10000, "window": 60},           # 10000次/分钟
        }
    }
    
    # Redis键过期时间（秒）
    KEY_EXPIRY = 3600  # 1小时
    
    # 紧急刹车阈值
    EMERGENCY_LIMITS = {
        "concurrent_requests": 1000,    # 并发请求数
        "error_rate_threshold": 0.5,    # 错误率阈值
        "response_time_threshold": 5.0,  # 响应时间阈值（秒）
    }


class RateLimitingService:
    """多维度限流服务"""
    
    def __init__(self):
        self.config = RateLimitConfig()
        
        # Redis连接
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', '')
        redis_db = int(os.getenv('REDIS_DB', '1'))
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True
            )
            # 客户端初始化（异步），不强制 ping 以避免同步环境阻塞
            logger.info("✅ 限流服务Redis连接成功")
        except Exception as e:
            logger.error(f"❌ 限流服务Redis连接失败: {str(e)}")
            self.redis_client = None
    
    async def check_rate_limit(self, 
                             user_id: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             endpoint: Optional[str] = None,
                             action: str = "default") -> Dict[str, Any]:
        """多维度限流检查"""
        
        if not self.redis_client:
            logger.warning("⚠️ Redis不可用，跳过限流检查")
            return {"allowed": True, "reason": "rate_limiting_disabled"}
        
        result = {
            "allowed": True,
            "blocked_by": [],
            "limits": {},
            "remaining": {},
            "reset_time": {},
            "retry_after": 0
        }
        
        try:
            current_time = time.time()
            
            # 1. 用户级限流检查
            if user_id:
                user_check = await self._check_user_rate_limit(user_id, action, current_time)
                result["limits"]["user"] = user_check["limit_info"]
                result["remaining"]["user"] = user_check["remaining"]
                result["reset_time"]["user"] = user_check["reset_time"]
                
                if not user_check["allowed"]:
                    result["allowed"] = False
                    result["blocked_by"].append("user_rate_limit")
                    result["retry_after"] = max(result["retry_after"], user_check["retry_after"])
            
            # 2. IP级限流检查
            if ip_address:
                ip_check = await self._check_ip_rate_limit(ip_address, action, current_time)
                result["limits"]["ip"] = ip_check["limit_info"]
                result["remaining"]["ip"] = ip_check["remaining"]
                result["reset_time"]["ip"] = ip_check["reset_time"]
                
                if not ip_check["allowed"]:
                    result["allowed"] = False
                    result["blocked_by"].append("ip_rate_limit")
                    result["retry_after"] = max(result["retry_after"], ip_check["retry_after"])
            
            # 3. 端点级限流检查
            if endpoint:
                endpoint_check = await self._check_endpoint_rate_limit(endpoint, action, current_time)
                result["limits"]["endpoint"] = endpoint_check["limit_info"]
                result["remaining"]["endpoint"] = endpoint_check["remaining"]
                result["reset_time"]["endpoint"] = endpoint_check["reset_time"]
                
                if not endpoint_check["allowed"]:
                    result["allowed"] = False
                    result["blocked_by"].append("endpoint_rate_limit")
                    result["retry_after"] = max(result["retry_after"], endpoint_check["retry_after"])
            
            # 4. 全局限流检查
            global_check = await self._check_global_rate_limit(action, current_time)
            result["limits"]["global"] = global_check["limit_info"]
            result["remaining"]["global"] = global_check["remaining"]
            result["reset_time"]["global"] = global_check["reset_time"]
            
            if not global_check["allowed"]:
                result["allowed"] = False
                result["blocked_by"].append("global_rate_limit")
                result["retry_after"] = max(result["retry_after"], global_check["retry_after"])
            
            # 5. 紧急刹车检查
            emergency_check = await self._check_emergency_brake()
            if not emergency_check["allowed"]:
                result["allowed"] = False
                result["blocked_by"].append("emergency_brake")
                result["retry_after"] = max(result["retry_after"], emergency_check["retry_after"])
            
            # 记录限流检查结果
            if result["blocked_by"]:
                logger.warning(f"🚫 请求被限流阻止: user_id={user_id}, ip={ip_address}, endpoint={endpoint}, "
                             f"blocked_by={result['blocked_by']}, retry_after={result['retry_after']}秒")
            
        except Exception as e:
            logger.error(f"❌ 限流检查失败: {str(e)}")
            # 发生错误时允许请求通过，但记录日志
            result["allowed"] = True
            result["error"] = str(e)
        
        return result
    
    async def _check_user_rate_limit(self, user_id: str, action: str, current_time: float) -> Dict[str, Any]:
        """检查用户级限流"""
        limits = self.config.DEFAULT_LIMITS[RateLimitType.USER]
        limit_config = limits.get(action, limits.get("default", {"limit": 100, "window": 60}))
        
        key = f"rate_limit:user:{user_id}:{action}"
        return await self._sliding_window_check(key, limit_config, current_time)
    
    async def _check_ip_rate_limit(self, ip_address: str, action: str, current_time: float) -> Dict[str, Any]:
        """检查IP级限流"""
        # 对敏感IP进行哈希处理
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        
        limits = self.config.DEFAULT_LIMITS[RateLimitType.IP]
        limit_config = limits.get(action, limits.get("default", {"limit": 500, "window": 60}))
        
        key = f"rate_limit:ip:{ip_hash}:{action}"
        return await self._sliding_window_check(key, limit_config, current_time)
    
    async def _check_endpoint_rate_limit(self, endpoint: str, action: str, current_time: float) -> Dict[str, Any]:
        """检查端点级限流"""
        limits = self.config.DEFAULT_LIMITS[RateLimitType.ENDPOINT]
        limit_config = limits.get(action, {"limit": 1000, "window": 60})
        
        key = f"rate_limit:endpoint:{endpoint}:{action}"
        return await self._sliding_window_check(key, limit_config, current_time)
    
    async def _check_global_rate_limit(self, action: str, current_time: float) -> Dict[str, Any]:
        """检查全局限流"""
        limits = self.config.DEFAULT_LIMITS[RateLimitType.GLOBAL]
        limit_config = limits.get(action, limits["default"])
        
        key = f"rate_limit:global:{action}"
        return await self._sliding_window_check(key, limit_config, current_time)
    
    async def _sliding_window_check(self, key: str, limit_config: Dict[str, int], current_time: float) -> Dict[str, Any]:
        """滑动窗口限流检查"""
        try:
            limit = limit_config["limit"]
            window = limit_config["window"]
            window_start = current_time - window
            
            # 使用Redis管道提高性能
            pipe = self.redis_client.pipeline()
            
            # 移除过期的记录
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 获取当前窗口内的请求数
            pipe.zcard(key)
            
            # 添加当前请求时间戳
            pipe.zadd(key, {str(current_time): current_time})
            
            # 设置过期时间
            pipe.expire(key, self.config.KEY_EXPIRY)
            
            results = await pipe.execute()
            current_count = results[1] + 1  # +1 因为包含当前请求
            
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset_time = current_time + window
            retry_after = window if not allowed else 0
            
            return {
                "allowed": allowed,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "limit_info": {
                    "limit": limit,
                    "window": window,
                    "current_count": current_count
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 滑动窗口限流检查失败: {key} - {str(e)}")
            # 错误时允许通过
            return {
                "allowed": True,
                "remaining": 0,
                "reset_time": current_time + 60,
                "retry_after": 0,
                "limit_info": {"limit": 0, "window": 0, "current_count": 0},
                "error": str(e)
            }
    
    async def _check_emergency_brake(self) -> Dict[str, Any]:
        """紧急刹车检查"""
        try:
            # 检查当前并发请求数
            concurrent_key = "emergency:concurrent_requests"
            concurrent_count = int(await self.redis_client.get(concurrent_key) or 0)
            
            if concurrent_count > self.config.EMERGENCY_LIMITS["concurrent_requests"]:
                logger.critical(f"🚨 紧急刹车触发 - 并发请求数过高: {concurrent_count}")
                return {
                    "allowed": False,
                    "retry_after": 60,
                    "reason": "high_concurrent_requests"
                }
            
            # 检查错误率（这里简化实现，实际可以更复杂）
            error_rate_key = "emergency:error_rate"
            error_rate = float(await self.redis_client.get(error_rate_key) or 0)
            
            if error_rate > self.config.EMERGENCY_LIMITS["error_rate_threshold"]:
                logger.critical(f"🚨 紧急刹车触发 - 错误率过高: {error_rate}")
                return {
                    "allowed": False,
                    "retry_after": 120,
                    "reason": "high_error_rate"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"❌ 紧急刹车检查失败: {str(e)}")
            return {"allowed": True}  # 错误时允许通过
    
    async def increment_concurrent_requests(self) -> int:
        """增加并发请求计数"""
        try:
            key = "emergency:concurrent_requests"
            current = await self.redis_client.incr(key)
            await self.redis_client.expire(key, 60)  # 1分钟过期
            return current
        except Exception as e:
            logger.error(f"❌ 增加并发计数失败: {str(e)}")
            return 0
    
    async def decrement_concurrent_requests(self) -> int:
        """减少并发请求计数"""
        try:
            key = "emergency:concurrent_requests"
            current = await self.redis_client.decr(key)
            return max(0, current)
        except Exception as e:
            logger.error(f"❌ 减少并发计数失败: {str(e)}")
            return 0
    
    async def record_request_result(self, success: bool, response_time: float):
        """记录请求结果，用于统计"""
        try:
            current_time = int(time.time())
            window_key = f"stats:{current_time // 60}"  # 按分钟分组
            
            pipe = self.redis_client.pipeline()
            
            # 记录请求统计
            pipe.hincrby(window_key, "total_requests", 1)
            if not success:
                pipe.hincrby(window_key, "error_requests", 1)
            
            # 记录响应时间
            pipe.lpush(f"response_times:{window_key}", response_time)
            pipe.ltrim(f"response_times:{window_key}", 0, 99)  # 保留最近100个
            
            # 设置过期时间
            pipe.expire(window_key, 3600)  # 1小时
            pipe.expire(f"response_times:{window_key}", 3600)
            
            await pipe.execute()
            
            # 计算并更新错误率
            await self._update_error_rate(window_key)
            
        except Exception as e:
            logger.error(f"❌ 记录请求结果失败: {str(e)}")
    
    async def _update_error_rate(self, window_key: str):
        """更新错误率"""
        try:
            stats = await self.redis_client.hgetall(window_key)
            if stats:
                total = int(stats.get("total_requests", 0))
                errors = int(stats.get("error_requests", 0))
                
                if total > 0:
                    error_rate = errors / total
                    await self.redis_client.setex("emergency:error_rate", 300, error_rate)
        except Exception as e:
            logger.error(f"❌ 更新错误率失败: {str(e)}")
    
    async def get_rate_limit_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取限流统计信息"""
        try:
            stats = {
                "concurrent_requests": 0,
                "error_rate": 0.0,
                "user_limits": {}
            }
            
            # 获取并发请求数
            concurrent_key = "emergency:concurrent_requests"
            stats["concurrent_requests"] = int(await self.redis_client.get(concurrent_key) or 0)
            
            # 获取错误率
            error_rate_key = "emergency:error_rate"
            stats["error_rate"] = float(await self.redis_client.get(error_rate_key) or 0.0)
            
            # 获取用户限流信息
            if user_id:
                current_time = time.time()
                for action in ["create_postcard", "login", "query_quota"]:
                    key = f"rate_limit:user:{user_id}:{action}"
                    limit_config = self.config.DEFAULT_LIMITS[RateLimitType.USER].get(action, {})
                    
                    if limit_config:
                        window_start = current_time - limit_config["window"]
                        current_count = await self.redis_client.zcount(key, window_start, current_time)
                        
                        stats["user_limits"][action] = {
                            "current": current_count,
                            "limit": limit_config["limit"],
                            "window": limit_config["window"],
                            "remaining": max(0, limit_config["limit"] - current_count)
                        }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取限流统计失败: {str(e)}")
            return {"error": str(e)}
