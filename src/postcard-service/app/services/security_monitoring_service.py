# -*- coding: utf-8 -*-
"""
安全监控服务
实现实时安全威胁检测、异常行为分析和告警机制
"""

import json
import time
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """威胁等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """安全事件类型"""
    MALICIOUS_INPUT = "malicious_input"
    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    INJECTION_ATTEMPT = "injection_attempt"


@dataclass
class SecurityEvent:
    """安全事件数据结构"""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    timestamp: float
    description: str
    metadata: Dict[str, Any]
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['threat_level'] = self.threat_level.value
        return data


class SecurityMonitoringService:
    """安全监控服务"""
    
    def __init__(self):
        # Redis连接
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', '')
        redis_db = int(os.getenv('REDIS_DB', '2'))  # 使用不同的数据库
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True
            )
            # 不在构造函数内执行异步 ping
            logger.info("✅ 安全监控服务Redis连接成功")
        except Exception as e:
            logger.error(f"❌ 安全监控服务Redis连接失败: {str(e)}")
            self.redis_client = None
        
        # 监控配置
        self.monitoring_enabled = os.getenv('SECURITY_MONITORING_ENABLED', 'true').lower() == 'true'
        self.alert_threshold = {
            ThreatLevel.LOW: 10,      # 10个低级威胁
            ThreatLevel.MEDIUM: 5,    # 5个中级威胁
            ThreatLevel.HIGH: 2,      # 2个高级威胁
            ThreatLevel.CRITICAL: 1   # 1个严重威胁
        }
        
        # 异常行为检测参数
        self.anomaly_config = {
            "login_attempts_threshold": 5,           # 登录尝试阈值
            "request_frequency_threshold": 100,      # 请求频率阈值（次/分钟）
            "different_ip_threshold": 3,             # 不同IP登录阈值
            "failed_requests_threshold": 10,         # 失败请求阈值
            "time_window": 300,                      # 时间窗口（秒）
        }
    
    async def record_security_event(self, event: SecurityEvent) -> bool:
        """记录安全事件"""
        if not self.monitoring_enabled or not self.redis_client:
            return True
        
        try:
            # 生成事件ID
            if not event.event_id:
                event.event_id = self._generate_event_id(event)
            
            # 存储事件
            event_key = f"security_event:{event.event_id}"
            event_data = event.to_dict()
            
            pipe = self.redis_client.pipeline()
            
            # 存储事件详情
            pipe.hset(event_key, mapping=event_data)
            pipe.expire(event_key, 86400 * 30)  # 30天过期
            
            # 添加到事件索引
            pipe.zadd("security_events:timeline", {event.event_id: event.timestamp})
            pipe.zadd(f"security_events:user:{event.user_id}", {event.event_id: event.timestamp})
            pipe.zadd(f"security_events:type:{event.event_type.value}", {event.event_id: event.timestamp})
            pipe.zadd(f"security_events:level:{event.threat_level.value}", {event.event_id: event.timestamp})
            
            # 更新统计信息
            current_hour = int(event.timestamp // 3600)
            stats_key = f"security_stats:{current_hour}"
            pipe.hincrby(stats_key, f"count:{event.event_type.value}", 1)
            pipe.hincrby(stats_key, f"level:{event.threat_level.value}", 1)
            pipe.expire(stats_key, 86400 * 7)  # 7天过期
            
            await pipe.execute()
            
            # 检查是否需要触发告警
            await self._check_alert_threshold(event)
            
            logger.info(f"✅ 安全事件已记录: {event.event_id} - {event.event_type.value} - {event.threat_level.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 记录安全事件失败: {str(e)}")
            return False
    
    async def detect_malicious_input(self, user_id: str, content: str, ip_address: str) -> Optional[SecurityEvent]:
        """检测恶意输入"""
        try:
            # 恶意模式检测
            malicious_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'on\w+\s*=',
                r'eval\s*\(',
                r'(union|select|insert|update|delete|drop)\s+',
                r'(\.\./|\.\.\\)',
                r'cmd\.exe',
                r'/bin/sh',
                r'<?php',
            ]
            
            import re
            detected_patterns = []
            for pattern in malicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_patterns.append(pattern)
            
            if detected_patterns:
                return SecurityEvent(
                    event_id="",
                    event_type=SecurityEventType.MALICIOUS_INPUT,
                    threat_level=ThreatLevel.HIGH,
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=None,
                    timestamp=time.time(),
                    description=f"检测到恶意输入模式: {', '.join(detected_patterns)}",
                    metadata={
                        "patterns": detected_patterns,
                        "content_length": len(content),
                        "content_preview": content[:100]  # 只保存前100个字符
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 恶意输入检测失败: {str(e)}")
            return None
    
    async def detect_brute_force_attack(self, user_id: str, ip_address: str, success: bool) -> Optional[SecurityEvent]:
        """检测暴力破解攻击"""
        if not self.redis_client:
            return None
        
        try:
            current_time = time.time()
            window_start = current_time - self.anomaly_config["time_window"]
            
            # 记录登录尝试
            attempt_key = f"login_attempts:{user_id}:{ip_address}"
            self.redis_client.zadd(attempt_key, {str(current_time): current_time})
            self.redis_client.zremrangebyscore(attempt_key, 0, window_start)
            self.redis_client.expire(attempt_key, self.anomaly_config["time_window"])
            
            # 统计失败次数
            if not success:
                fail_key = f"login_failures:{user_id}:{ip_address}"
                self.redis_client.zadd(fail_key, {str(current_time): current_time})
                self.redis_client.zremrangebyscore(fail_key, 0, window_start)
                self.redis_client.expire(fail_key, self.anomaly_config["time_window"])
                
                failure_count = self.redis_client.zcard(fail_key)
                
                if failure_count >= self.anomaly_config["login_attempts_threshold"]:
                    return SecurityEvent(
                        event_id="",
                        event_type=SecurityEventType.BRUTE_FORCE,
                        threat_level=ThreatLevel.HIGH,
                        user_id=user_id,
                        ip_address=ip_address,
                        endpoint="login",
                        timestamp=current_time,
                        description=f"检测到暴力破解攻击: {failure_count} 次失败登录尝试",
                        metadata={
                            "failure_count": failure_count,
                            "time_window": self.anomaly_config["time_window"],
                            "threshold": self.anomaly_config["login_attempts_threshold"]
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 暴力破解检测失败: {str(e)}")
            return None
    
    async def detect_suspicious_behavior(self, user_id: str, ip_address: str, user_agent: str, endpoint: str) -> Optional[SecurityEvent]:
        """检测可疑行为"""
        if not self.redis_client:
            return None
        
        try:
            current_time = time.time()
            window_start = current_time - self.anomaly_config["time_window"]
            
            # 1. 检测异常请求频率
            freq_key = f"request_frequency:{user_id}"
            self.redis_client.zadd(freq_key, {str(current_time): current_time})
            self.redis_client.zremrangebyscore(freq_key, 0, window_start)
            self.redis_client.expire(freq_key, self.anomaly_config["time_window"])
            
            request_count = self.redis_client.zcard(freq_key)
            
            if request_count > self.anomaly_config["request_frequency_threshold"]:
                return SecurityEvent(
                    event_id="",
                    event_type=SecurityEventType.SUSPICIOUS_BEHAVIOR,
                    threat_level=ThreatLevel.MEDIUM,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    timestamp=current_time,
                    description=f"异常请求频率: {request_count} 次请求在 {self.anomaly_config['time_window']} 秒内",
                    metadata={
                        "request_count": request_count,
                        "threshold": self.anomaly_config["request_frequency_threshold"],
                        "detection_type": "high_frequency"
                    }
                )
            
            # 2. 检测多IP登录
            if endpoint == "login":
                ip_key = f"login_ips:{user_id}"
                self.redis_client.sadd(ip_key, ip_address)
                self.redis_client.expire(ip_key, self.anomaly_config["time_window"])
                
                ip_count = self.redis_client.scard(ip_key)
                
                if ip_count > self.anomaly_config["different_ip_threshold"]:
                    return SecurityEvent(
                        event_id="",
                        event_type=SecurityEventType.SUSPICIOUS_BEHAVIOR,
                        threat_level=ThreatLevel.MEDIUM,
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        endpoint=endpoint,
                        timestamp=current_time,
                        description=f"多IP登录检测: {ip_count} 个不同IP地址",
                        metadata={
                            "ip_count": ip_count,
                            "threshold": self.anomaly_config["different_ip_threshold"],
                            "detection_type": "multiple_ips"
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 可疑行为检测失败: {str(e)}")
            return None
    
    async def detect_unauthorized_access(self, user_id: str, resource: str, required_permission: str, ip_address: str) -> Optional[SecurityEvent]:
        """检测未授权访问"""
        try:
            return SecurityEvent(
                event_id="",
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                threat_level=ThreatLevel.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                endpoint=resource,
                timestamp=time.time(),
                description=f"未授权访问尝试: 用户尝试访问需要 {required_permission} 权限的资源 {resource}",
                metadata={
                    "resource": resource,
                    "required_permission": required_permission,
                    "access_denied": True
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 未授权访问检测失败: {str(e)}")
            return None
    
    async def _check_alert_threshold(self, event: SecurityEvent):
        """检查告警阈值"""
        if not self.redis_client:
            return
        
        try:
            # 统计最近1小时内同级别事件数量
            current_time = time.time()
            one_hour_ago = current_time - 3600
            
            level_key = f"security_events:level:{event.threat_level.value}"
            recent_count = self.redis_client.zcount(level_key, one_hour_ago, current_time)
            
            threshold = self.alert_threshold.get(event.threat_level, float('inf'))
            
            if recent_count >= threshold:
                await self._trigger_security_alert(event.threat_level, recent_count, threshold)
                
        except Exception as e:
            logger.error(f"❌ 检查告警阈值失败: {str(e)}")
    
    async def _trigger_security_alert(self, threat_level: ThreatLevel, count: int, threshold: int):
        """触发安全告警"""
        try:
            alert_data = {
                "threat_level": threat_level.value,
                "event_count": count,
                "threshold": threshold,
                "timestamp": time.time(),
                "message": f"安全告警: {threat_level.value}级威胁事件在1小时内发生了{count}次，超过阈值{threshold}"
            }
            
            # 存储告警记录
            alert_key = f"security_alert:{int(time.time())}"
            self.redis_client.hset(alert_key, mapping=alert_data)
            self.redis_client.expire(alert_key, 86400 * 7)  # 7天过期
            
            # 添加到告警时间线
            self.redis_client.zadd("security_alerts:timeline", {alert_key: time.time()})
            
            # 记录日志
            logger.critical(f"🚨 {alert_data['message']}")
            
            # 这里可以集成邮件、短信、Webhook等告警通知
            # await self._send_alert_notification(alert_data)
            
        except Exception as e:
            logger.error(f"❌ 触发安全告警失败: {str(e)}")
    
    async def get_security_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """获取安全仪表板数据"""
        if not self.redis_client:
            return {"error": "Redis不可用"}
        
        try:
            current_time = time.time()
            time_window = hours * 3600
            window_start = current_time - time_window
            
            dashboard = {
                "time_range": {
                    "start": window_start,
                    "end": current_time,
                    "hours": hours
                },
                "events": {
                    "total": 0,
                    "by_type": {},
                    "by_level": {}
                },
                "alerts": [],
                "top_threats": [],
                "recent_events": []
            }
            
            # 统计事件总数
            total_events = self.redis_client.zcount("security_events:timeline", window_start, current_time)
            dashboard["events"]["total"] = total_events
            
            # 按类型统计
            for event_type in SecurityEventType:
                type_key = f"security_events:type:{event_type.value}"
                count = self.redis_client.zcount(type_key, window_start, current_time)
                if count > 0:
                    dashboard["events"]["by_type"][event_type.value] = count
            
            # 按级别统计
            for threat_level in ThreatLevel:
                level_key = f"security_events:level:{threat_level.value}"
                count = self.redis_client.zcount(level_key, window_start, current_time)
                if count > 0:
                    dashboard["events"]["by_level"][threat_level.value] = count
            
            # 获取最近告警
            recent_alerts = self.redis_client.zrevrangebyscore(
                "security_alerts:timeline", current_time, window_start, 
                start=0, num=10, withscores=True
            )
            
            for alert_key, timestamp in recent_alerts:
                alert_data = self.redis_client.hgetall(alert_key)
                if alert_data:
                    alert_data["timestamp"] = timestamp
                    dashboard["alerts"].append(alert_data)
            
            # 获取最近事件
            recent_event_ids = self.redis_client.zrevrangebyscore(
                "security_events:timeline", current_time, window_start,
                start=0, num=20
            )
            
            for event_id in recent_event_ids:
                event_key = f"security_event:{event_id}"
                event_data = self.redis_client.hgetall(event_key)
                if event_data:
                    dashboard["recent_events"].append(event_data)
            
            return dashboard
            
        except Exception as e:
            logger.error(f"❌ 获取安全仪表板失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_user_security_profile(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """获取用户安全画像"""
        if not self.redis_client:
            return {"error": "Redis不可用"}
        
        try:
            current_time = time.time()
            time_window = days * 24 * 3600
            window_start = current_time - time_window
            
            profile = {
                "user_id": user_id,
                "time_range": {
                    "start": window_start,
                    "end": current_time,
                    "days": days
                },
                "security_events": [],
                "risk_score": 0,
                "behavior_pattern": {}
            }
            
            # 获取用户相关的安全事件
            user_event_key = f"security_events:user:{user_id}"
            event_ids = self.redis_client.zrevrangebyscore(
                user_event_key, current_time, window_start
            )
            
            risk_score = 0
            event_counts = {}
            
            for event_id in event_ids:
                event_key = f"security_event:{event_id}"
                event_data = self.redis_client.hgetall(event_key)
                if event_data:
                    profile["security_events"].append(event_data)
                    
                    # 计算风险分数
                    threat_level = event_data.get("threat_level", "low")
                    risk_weights = {"low": 1, "medium": 3, "high": 5, "critical": 10}
                    risk_score += risk_weights.get(threat_level, 1)
                    
                    # 统计事件类型
                    event_type = event_data.get("event_type", "unknown")
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            profile["risk_score"] = risk_score
            profile["event_counts"] = event_counts
            
            # 行为模式分析（简化版）
            if risk_score > 20:
                profile["risk_level"] = "high"
            elif risk_score > 10:
                profile["risk_level"] = "medium"
            elif risk_score > 5:
                profile["risk_level"] = "low"
            else:
                profile["risk_level"] = "minimal"
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ 获取用户安全画像失败: {str(e)}")
            return {"error": str(e)}
    
    def _generate_event_id(self, event: SecurityEvent) -> str:
        """生成事件ID"""
        content = f"{event.event_type.value}:{event.user_id}:{event.ip_address}:{event.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def cleanup_old_events(self, days: int = 30):
        """清理旧的安全事件"""
        if not self.redis_client:
            return
        
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            
            # 清理时间线索引
            self.redis_client.zremrangebyscore("security_events:timeline", 0, cutoff_time)
            self.redis_client.zremrangebyscore("security_alerts:timeline", 0, cutoff_time)
            
            # 清理各种索引
            for event_type in SecurityEventType:
                type_key = f"security_events:type:{event_type.value}"
                self.redis_client.zremrangebyscore(type_key, 0, cutoff_time)
            
            for threat_level in ThreatLevel:
                level_key = f"security_events:level:{threat_level.value}"
                self.redis_client.zremrangebyscore(level_key, 0, cutoff_time)
            
            logger.info(f"✅ 已清理 {days} 天前的安全事件")
            
        except Exception as e:
            logger.error(f"❌ 清理旧事件失败: {str(e)}")
