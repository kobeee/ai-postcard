# -*- coding: utf-8 -*-
"""
实时监控告警服务
监控系统健康状态，触发告警和自动恢复机制
"""

import time
import json
import asyncio
import logging
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import redis
import os
import psutil
import httpx
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """指标类型"""
    SYSTEM_CPU = "system_cpu"
    SYSTEM_MEMORY = "system_memory"
    SYSTEM_DISK = "system_disk"
    DATABASE_CONNECTIONS = "database_connections"
    REDIS_CONNECTIONS = "redis_connections"
    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    SECURITY_EVENTS = "security_events"
    AUDIT_LOGS = "audit_logs"


@dataclass
class MetricValue:
    """指标值"""
    metric_type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels or {}
        }


@dataclass 
class Alert:
    """告警对象"""
    alert_id: str
    metric_type: MetricType
    level: AlertLevel
    title: str
    message: str
    timestamp: float
    value: float
    threshold: float
    labels: Dict[str, str] = None
    resolved: bool = False
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['level'] = self.level.value
        return data


class MonitoringService:
    """实时监控服务"""
    
    def __init__(self):
        # Redis连接
        self.redis_client = self._setup_redis()
        
        # 配置
        self.monitoring_enabled = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
        self.alert_enabled = os.getenv('ALERT_ENABLED', 'true').lower() == 'true'
        self.webhook_url = os.getenv('MONITORING_WEBHOOK_URL', '')
        self.email_alerts = os.getenv('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true'
        
        # 告警阈值配置
        self.thresholds = {
            MetricType.SYSTEM_CPU: {"warning": 70, "critical": 90},
            MetricType.SYSTEM_MEMORY: {"warning": 80, "critical": 95},
            MetricType.SYSTEM_DISK: {"warning": 85, "critical": 95},
            MetricType.ERROR_RATE: {"warning": 0.05, "critical": 0.1},  # 5%, 10%
            MetricType.RESPONSE_TIME: {"warning": 2000, "critical": 5000},  # 毫秒
            MetricType.DATABASE_CONNECTIONS: {"warning": 80, "critical": 95},
            MetricType.REDIS_CONNECTIONS: {"warning": 80, "critical": 95},
        }
        
        # 监控间隔
        self.collection_interval = int(os.getenv('MONITORING_INTERVAL', '60'))  # 60秒
        self.alert_cooldown = int(os.getenv('ALERT_COOLDOWN', '300'))  # 5分钟
        
        # 运行状态
        self.is_running = False
        self._tasks = []
        
        logger.info(f"📊 监控服务初始化: enabled={self.monitoring_enabled}, alerts={self.alert_enabled}")
    
    def _setup_redis(self) -> Optional[redis.Redis]:
        """设置Redis连接"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD', '')
            redis_db = int(os.getenv('REDIS_DB_MONITORING', '4'))
            
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True
            )
            client.ping()
            logger.info("✅ 监控服务Redis连接成功")
            return client
        except Exception as e:
            logger.error(f"❌ 监控服务Redis连接失败: {str(e)}")
            return None
    
    async def start_monitoring(self):
        """启动监控"""
        if not self.monitoring_enabled or self.is_running:
            return
        
        self.is_running = True
        logger.info("🚀 开始监控系统指标")
        
        # 启动监控任务
        self._tasks = [
            asyncio.create_task(self._collect_system_metrics()),
            asyncio.create_task(self._collect_application_metrics()),
            asyncio.create_task(self._process_alerts()),
            asyncio.create_task(self._cleanup_old_data())
        ]
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("🔄 监控服务已停止")
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                await self._record_metric(MetricValue(
                    MetricType.SYSTEM_CPU, cpu_percent, current_time
                ))
                
                # 内存使用率
                memory = psutil.virtual_memory()
                await self._record_metric(MetricValue(
                    MetricType.SYSTEM_MEMORY, memory.percent, current_time
                ))
                
                # 磁盘使用率
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                await self._record_metric(MetricValue(
                    MetricType.SYSTEM_DISK, disk_percent, current_time
                ))
                
                logger.debug(f"📊 系统指标收集完成: CPU={cpu_percent:.1f}%, 内存={memory.percent:.1f}%, 磁盘={disk_percent:.1f}%")
                
            except Exception as e:
                logger.error(f"❌ 系统指标收集失败: {str(e)}")
            
            await asyncio.sleep(self.collection_interval)
    
    async def _collect_application_metrics(self):
        """收集应用指标"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # 数据库连接数（如果有Redis客户端）
                if self.redis_client:
                    try:
                        db_info = self.redis_client.info()
                        connected_clients = db_info.get('connected_clients', 0)
                        max_clients = db_info.get('maxclients', 10000)
                        
                        if max_clients > 0:
                            connection_percent = (connected_clients / max_clients) * 100
                            await self._record_metric(MetricValue(
                                MetricType.REDIS_CONNECTIONS, connection_percent, current_time
                            ))
                    except Exception as e:
                        logger.debug(f"Redis连接指标收集失败: {str(e)}")
                
                # 从统计数据收集错误率和响应时间
                await self._collect_error_rate_metrics(current_time)
                await self._collect_response_time_metrics(current_time)
                
                logger.debug("📊 应用指标收集完成")
                
            except Exception as e:
                logger.error(f"❌ 应用指标收集失败: {str(e)}")
            
            await asyncio.sleep(self.collection_interval)
    
    async def _collect_error_rate_metrics(self, current_time: float):
        """收集错误率指标"""
        try:
            if not self.redis_client:
                return
            
            # 从最近1小时的统计数据计算错误率
            current_hour = int(current_time // 3600)
            
            total_requests = 0
            error_requests = 0
            
            # 检查最近几个小时窗口的统计
            for i in range(1):  # 只看最近1小时
                hour_key = f"stats:{current_hour - i}"
                stats = self.redis_client.hgetall(hour_key)
                
                if stats:
                    total_requests += int(stats.get("total_requests", 0))
                    error_requests += int(stats.get("error_requests", 0))
            
            if total_requests > 0:
                error_rate = error_requests / total_requests
                await self._record_metric(MetricValue(
                    MetricType.ERROR_RATE, error_rate, current_time
                ))
            
        except Exception as e:
            logger.debug(f"错误率指标收集失败: {str(e)}")
    
    async def _collect_response_time_metrics(self, current_time: float):
        """收集响应时间指标"""
        try:
            if not self.redis_client:
                return
            
            # 从最近的响应时间数据计算平均值
            current_window = int(current_time // 60)  # 按分钟分组
            response_times_key = f"response_times:stats:{current_window}"
            
            response_times = self.redis_client.lrange(response_times_key, 0, -1)
            
            if response_times:
                times = [float(t) for t in response_times]
                avg_response_time = sum(times) / len(times) * 1000  # 转换为毫秒
                await self._record_metric(MetricValue(
                    MetricType.RESPONSE_TIME, avg_response_time, current_time
                ))
            
        except Exception as e:
            logger.debug(f"响应时间指标收集失败: {str(e)}")
    
    async def _record_metric(self, metric: MetricValue):
        """记录指标值"""
        try:
            if not self.redis_client:
                return
            
            # 存储指标值
            metric_key = f"metrics:{metric.metric_type.value}"
            self.redis_client.zadd(metric_key, {
                json.dumps(metric.to_dict()): metric.timestamp
            })
            
            # 保留最近24小时的数据
            cutoff_time = time.time() - 24 * 3600
            self.redis_client.zremrangebyscore(metric_key, 0, cutoff_time)
            
            # 检查是否需要告警
            await self._check_alert_thresholds(metric)
            
        except Exception as e:
            logger.error(f"❌ 记录指标失败: {str(e)}")
    
    async def _check_alert_thresholds(self, metric: MetricValue):
        """检查告警阈值"""
        if not self.alert_enabled:
            return
        
        try:
            thresholds = self.thresholds.get(metric.metric_type)
            if not thresholds:
                return
            
            alert_level = None
            threshold = 0
            
            if metric.value >= thresholds.get("critical", float('inf')):
                alert_level = AlertLevel.CRITICAL
                threshold = thresholds["critical"]
            elif metric.value >= thresholds.get("warning", float('inf')):
                alert_level = AlertLevel.WARNING
                threshold = thresholds["warning"]
            
            if alert_level:
                # 检查告警冷却期
                if not await self._is_in_cooldown(metric.metric_type, alert_level):
                    await self._trigger_alert(metric, alert_level, threshold)
            else:
                # 检查是否需要解除告警
                await self._resolve_alerts(metric.metric_type)
                
        except Exception as e:
            logger.error(f"❌ 告警阈值检查失败: {str(e)}")
    
    async def _is_in_cooldown(self, metric_type: MetricType, level: AlertLevel) -> bool:
        """检查是否在告警冷却期内"""
        try:
            if not self.redis_client:
                return False
            
            cooldown_key = f"alert_cooldown:{metric_type.value}:{level.value}"
            last_alert = self.redis_client.get(cooldown_key)
            
            if last_alert:
                last_time = float(last_alert)
                if time.time() - last_time < self.alert_cooldown:
                    return True
            
            return False
        except:
            return False
    
    async def _trigger_alert(self, metric: MetricValue, level: AlertLevel, threshold: float):
        """触发告警"""
        try:
            alert_id = hashlib.md5(
                f"{metric.metric_type.value}:{level.value}:{int(time.time())}".encode()
            ).hexdigest()[:16]
            
            alert = Alert(
                alert_id=alert_id,
                metric_type=metric.metric_type,
                level=level,
                title=f"{metric.metric_type.value.upper()}告警",
                message=f"{metric.metric_type.value}指标异常: 当前值{metric.value:.2f}，超过{level.value}阈值{threshold}",
                timestamp=metric.timestamp,
                value=metric.value,
                threshold=threshold,
                labels=metric.labels
            )
            
            # 存储告警记录
            await self._store_alert(alert)
            
            # 设置冷却期
            if self.redis_client:
                cooldown_key = f"alert_cooldown:{metric.metric_type.value}:{level.value}"
                self.redis_client.setex(cooldown_key, self.alert_cooldown, time.time())
            
            # 发送告警通知
            await self._send_alert_notification(alert)
            
            logger.warning(f"🚨 告警触发: {alert.title} - {alert.message}")
            
        except Exception as e:
            logger.error(f"❌ 触发告警失败: {str(e)}")
    
    async def _store_alert(self, alert: Alert):
        """存储告警记录"""
        try:
            if not self.redis_client:
                return
            
            # 存储告警详情
            alert_key = f"alert:{alert.alert_id}"
            self.redis_client.hset(alert_key, mapping=alert.to_dict())
            self.redis_client.expire(alert_key, 86400 * 7)  # 7天过期
            
            # 添加到告警时间线
            self.redis_client.zadd("alerts:timeline", {alert.alert_id: alert.timestamp})
            
            # 添加到级别索引
            level_key = f"alerts:level:{alert.level.value}"
            self.redis_client.zadd(level_key, {alert.alert_id: alert.timestamp})
            
            # 添加到指标类型索引
            metric_key = f"alerts:metric:{alert.metric_type.value}"
            self.redis_client.zadd(metric_key, {alert.alert_id: alert.timestamp})
            
            # 未解决告警索引
            if not alert.resolved:
                self.redis_client.sadd("alerts:unresolved", alert.alert_id)
            
        except Exception as e:
            logger.error(f"❌ 存储告警记录失败: {str(e)}")
    
    async def _resolve_alerts(self, metric_type: MetricType):
        """解除告警"""
        try:
            if not self.redis_client:
                return
            
            # 查找该指标的未解决告警
            unresolved_alerts = self.redis_client.smembers("alerts:unresolved")
            
            for alert_id in unresolved_alerts:
                alert_key = f"alert:{alert_id}"
                alert_data = self.redis_client.hgetall(alert_key)
                
                if alert_data and alert_data.get("metric_type") == metric_type.value:
                    # 标记为已解决
                    alert_data["resolved"] = "true"
                    alert_data["resolved_at"] = str(time.time())
                    
                    self.redis_client.hset(alert_key, mapping=alert_data)
                    self.redis_client.srem("alerts:unresolved", alert_id)
                    
                    logger.info(f"✅ 告警已解除: {alert_id} - {metric_type.value}")
        
        except Exception as e:
            logger.error(f"❌ 解除告警失败: {str(e)}")
    
    async def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        try:
            # Webhook通知
            if self.webhook_url:
                await self._send_webhook_alert(alert)
            
            # 邮件通知（如果启用）
            if self.email_alerts:
                await self._send_email_alert(alert)
                
        except Exception as e:
            logger.error(f"❌ 发送告警通知失败: {str(e)}")
    
    async def _send_webhook_alert(self, alert: Alert):
        """发送Webhook告警"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "metric_type": alert.metric_type.value,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp,
                    "service": "ai-postcard-monitoring"
                }
                
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Webhook告警发送成功: {alert.alert_id}")
                else:
                    logger.error(f"❌ Webhook告警发送失败: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Webhook告警发送异常: {str(e)}")
    
    async def _send_email_alert(self, alert: Alert):
        """发送邮件告警"""
        # TODO: 集成邮件服务
        logger.info(f"📧 邮件告警: {alert.title} - {alert.message}")
    
    async def _process_alerts(self):
        """处理告警队列"""
        while self.is_running:
            try:
                # 这里可以处理告警的后续流程
                # 比如自动恢复、升级等
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"❌ 处理告警队列失败: {str(e)}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_data(self):
        """清理旧数据"""
        while self.is_running:
            try:
                if not self.redis_client:
                    await asyncio.sleep(3600)  # 1小时后重试
                    continue
                
                current_time = time.time()
                cutoff_time = current_time - 7 * 24 * 3600  # 7天前
                
                # 清理旧的指标数据
                for metric_type in MetricType:
                    metric_key = f"metrics:{metric_type.value}"
                    self.redis_client.zremrangebyscore(metric_key, 0, cutoff_time)
                
                # 清理旧的告警数据
                self.redis_client.zremrangebyscore("alerts:timeline", 0, cutoff_time)
                
                for level in AlertLevel:
                    level_key = f"alerts:level:{level.value}"
                    self.redis_client.zremrangebyscore(level_key, 0, cutoff_time)
                
                logger.info("🧹 旧监控数据清理完成")
                
            except Exception as e:
                logger.error(f"❌ 清理旧数据失败: {str(e)}")
            
            await asyncio.sleep(3600)  # 每小时清理一次
    
    async def get_metrics(self, 
                         metric_type: MetricType, 
                         hours: int = 1) -> List[Dict[str, Any]]:
        """获取指标数据"""
        try:
            if not self.redis_client:
                return []
            
            current_time = time.time()
            start_time = current_time - hours * 3600
            
            metric_key = f"metrics:{metric_type.value}"
            metric_data = self.redis_client.zrangebyscore(
                metric_key, start_time, current_time, withscores=True
            )
            
            metrics = []
            for data_str, timestamp in metric_data:
                try:
                    data = json.loads(data_str)
                    metrics.append(data)
                except:
                    continue
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ 获取指标数据失败: {str(e)}")
            return []
    
    async def get_alerts(self, 
                        level: Optional[AlertLevel] = None,
                        resolved: Optional[bool] = None,
                        hours: int = 24,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警记录"""
        try:
            if not self.redis_client:
                return []
            
            current_time = time.time()
            start_time = current_time - hours * 3600
            
            # 确定查询键
            if level:
                query_key = f"alerts:level:{level.value}"
            else:
                query_key = "alerts:timeline"
            
            # 获取告警ID列表
            alert_ids = self.redis_client.zrevrangebyscore(
                query_key, current_time, start_time, 
                start=0, num=limit
            )
            
            # 获取详细告警信息
            alerts = []
            for alert_id in alert_ids:
                alert_key = f"alert:{alert_id}"
                alert_data = self.redis_client.hgetall(alert_key)
                
                if alert_data:
                    # 类型转换
                    alert_data['timestamp'] = float(alert_data['timestamp'])
                    alert_data['value'] = float(alert_data['value'])
                    alert_data['threshold'] = float(alert_data['threshold'])
                    alert_data['resolved'] = alert_data.get('resolved', 'false').lower() == 'true'
                    
                    if alert_data.get('resolved_at'):
                        alert_data['resolved_at'] = float(alert_data['resolved_at'])
                    
                    # 过滤resolved状态
                    if resolved is not None:
                        if alert_data['resolved'] != resolved:
                            continue
                    
                    alerts.append(alert_data)
            
            return alerts
            
        except Exception as e:
            logger.error(f"❌ 获取告警记录失败: {str(e)}")
            return []
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            health = {
                "status": "healthy",
                "timestamp": time.time(),
                "metrics": {},
                "alerts": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "unresolved": 0
                },
                "services": {}
            }
            
            # 获取最新指标
            for metric_type in [MetricType.SYSTEM_CPU, MetricType.SYSTEM_MEMORY, 
                               MetricType.SYSTEM_DISK, MetricType.ERROR_RATE]:
                recent_metrics = await self.get_metrics(metric_type, hours=0.1)  # 最近6分钟
                if recent_metrics:
                    latest_metric = recent_metrics[-1]
                    health["metrics"][metric_type.value] = latest_metric["value"]
            
            # 获取告警统计
            recent_alerts = await self.get_alerts(hours=24)
            health["alerts"]["total"] = len(recent_alerts)
            
            for alert in recent_alerts:
                level = alert.get("level", "info")
                if level == "critical":
                    health["alerts"]["critical"] += 1
                elif level == "warning":
                    health["alerts"]["warning"] += 1
                
                if not alert.get("resolved", True):
                    health["alerts"]["unresolved"] += 1
            
            # 服务健康检查
            health["services"]["redis"] = self._check_redis_health()
            health["services"]["monitoring"] = self.is_running
            
            # 判断整体健康状态
            if health["alerts"]["critical"] > 0:
                health["status"] = "critical"
            elif health["alerts"]["warning"] > 0:
                health["status"] = "warning"
            elif health["alerts"]["unresolved"] > 5:
                health["status"] = "degraded"
            
            return health
            
        except Exception as e:
            logger.error(f"❌ 获取系统健康状态失败: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _check_redis_health(self) -> bool:
        """检查Redis健康状态"""
        try:
            if not self.redis_client:
                return False
            self.redis_client.ping()
            return True
        except:
            return False


# 全局监控服务实例
monitoring_service = None


def get_monitoring_service() -> MonitoringService:
    """获取全局监控服务实例"""
    global monitoring_service
    if not monitoring_service:
        monitoring_service = MonitoringService()
    return monitoring_service