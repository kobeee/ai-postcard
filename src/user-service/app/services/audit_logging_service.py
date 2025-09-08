# -*- coding: utf-8 -*-
"""
审计日志服务
记录系统关键操作，支持法规合规和安全审计
"""

import json
import time
import uuid
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import redis
import os
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 审计日志数据库表定义
Base = declarative_base()


class AuditOperationType(Enum):
    """审计操作类型"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    POSTCARD_CREATE = "postcard_create"
    POSTCARD_DELETE = "postcard_delete"
    POSTCARD_VIEW = "postcard_view"
    QUOTA_CONSUME = "quota_consume"
    QUOTA_RESTORE = "quota_restore"
    PERMISSION_CHECK = "permission_check"
    SECURITY_EVENT = "security_event"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    ADMIN_OPERATION = "admin_operation"


class AuditResult(Enum):
    """审计结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    log_id: str
    operation_type: AuditOperationType
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: float
    result: AuditResult
    resource: Optional[str]
    details: Dict[str, Any]
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['operation_type'] = self.operation_type.value
        data['result'] = self.result.value
        return data


class AuditLog(Base):
    """审计日志表模型"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    operation_type = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    resource = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON字符串
    session_id = Column(String, nullable=True, index=True)
    trace_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLoggingService:
    """审计日志服务"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        
        # 配置
        self.audit_enabled = os.getenv('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true'
        self.store_in_db = os.getenv('AUDIT_STORE_DB', 'true').lower() == 'true'
        self.store_in_redis = os.getenv('AUDIT_STORE_REDIS', 'true').lower() == 'true'
        self.log_sensitive_data = os.getenv('LOG_SENSITIVE_DATA', 'false').lower() == 'true'
        
        # Redis连接
        if self.store_in_redis:
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', '6379'))
                redis_password = os.getenv('REDIS_PASSWORD', '')
                redis_db = int(os.getenv('REDIS_DB_AUDIT', '3'))  # 审计专用数据库
                
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("✅ 审计日志Redis连接成功")
            except Exception as e:
                logger.error(f"❌ 审计日志Redis连接失败: {str(e)}")
                self.redis_client = None
                self.store_in_redis = False
        else:
            self.redis_client = None
        
        # 数据库连接（如果未提供session）
        if self.store_in_db and not self.db_session:
            try:
                db_url = self._get_database_url()
                self.engine = create_engine(db_url)
                SessionLocal = sessionmaker(bind=self.engine)
                self.db_session = SessionLocal()
                
                # 创建表（如果不存在）
                Base.metadata.create_all(bind=self.engine)
                logger.info("✅ 审计日志数据库连接成功")
            except Exception as e:
                logger.error(f"❌ 审计日志数据库连接失败: {str(e)}")
                self.store_in_db = False
        
        logger.info(f"🔍 审计日志服务初始化: enabled={self.audit_enabled}, db={self.store_in_db}, redis={self.store_in_redis}")
    
    async def log_operation(self, 
                          operation_type: AuditOperationType,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          result: AuditResult = AuditResult.SUCCESS,
                          resource: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None,
                          session_id: Optional[str] = None,
                          trace_id: Optional[str] = None) -> bool:
        """记录审计操作"""
        
        if not self.audit_enabled:
            return True
        
        try:
            # 创建审计日志条目
            log_entry = AuditLogEntry(
                log_id=str(uuid.uuid4()),
                operation_type=operation_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=time.time(),
                result=result,
                resource=resource,
                details=self._sanitize_details(details or {}),
                session_id=session_id,
                trace_id=trace_id
            )
            
            # 存储到Redis
            if self.store_in_redis and self.redis_client:
                await self._store_to_redis(log_entry)
            
            # 存储到数据库
            if self.store_in_db and self.db_session:
                await self._store_to_database(log_entry)
            
            # 写入日志文件
            await self._write_to_log_file(log_entry)
            
            logger.debug(f"✅ 审计日志记录成功: {operation_type.value} - {user_id} - {result.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 审计日志记录失败: {str(e)}")
            return False
    
    async def _store_to_redis(self, log_entry: AuditLogEntry):
        """存储到Redis"""
        try:
            # 存储详细日志
            log_key = f"audit_log:{log_entry.log_id}"
            self.redis_client.hset(log_key, mapping=log_entry.to_dict())
            self.redis_client.expire(log_key, 86400 * 90)  # 90天过期
            
            # 添加到时间线索引
            timeline_key = "audit_logs:timeline"
            self.redis_client.zadd(timeline_key, {log_entry.log_id: log_entry.timestamp})
            
            # 添加到用户索引
            if log_entry.user_id:
                user_key = f"audit_logs:user:{log_entry.user_id}"
                self.redis_client.zadd(user_key, {log_entry.log_id: log_entry.timestamp})
                self.redis_client.expire(user_key, 86400 * 30)  # 30天过期
            
            # 添加到操作类型索引
            type_key = f"audit_logs:type:{log_entry.operation_type.value}"
            self.redis_client.zadd(type_key, {log_entry.log_id: log_entry.timestamp})
            
            # 添加到结果索引
            result_key = f"audit_logs:result:{log_entry.result.value}"
            self.redis_client.zadd(result_key, {log_entry.log_id: log_entry.timestamp})
            
            # 统计信息
            current_hour = int(log_entry.timestamp // 3600)
            stats_key = f"audit_stats:{current_hour}"
            self.redis_client.hincrby(stats_key, f"count:{log_entry.operation_type.value}", 1)
            self.redis_client.hincrby(stats_key, f"result:{log_entry.result.value}", 1)
            self.redis_client.expire(stats_key, 86400 * 7)  # 7天过期
            
        except Exception as e:
            logger.error(f"❌ Redis审计日志存储失败: {str(e)}")
            raise
    
    async def _store_to_database(self, log_entry: AuditLogEntry):
        """存储到数据库"""
        try:
            audit_log = AuditLog(
                id=log_entry.log_id,
                operation_type=log_entry.operation_type.value,
                user_id=log_entry.user_id,
                ip_address=log_entry.ip_address,
                user_agent=log_entry.user_agent,
                timestamp=datetime.fromtimestamp(log_entry.timestamp),
                result=log_entry.result.value,
                resource=log_entry.resource,
                details=json.dumps(log_entry.details, ensure_ascii=False),
                session_id=log_entry.session_id,
                trace_id=log_entry.trace_id
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"❌ 数据库审计日志存储失败: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            raise
    
    async def _write_to_log_file(self, log_entry: AuditLogEntry):
        """写入日志文件"""
        try:
            audit_logger = logging.getLogger("audit")
            if not audit_logger.handlers:
                # 配置审计专用日志
                from logging.handlers import RotatingFileHandler
                log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                os.makedirs(log_dir, exist_ok=True)
                
                handler = RotatingFileHandler(
                    os.path.join(log_dir, 'audit.log'),
                    maxBytes=50*1024*1024,  # 50MB
                    backupCount=10
                )
                formatter = logging.Formatter(
                    '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                audit_logger.addHandler(handler)
                audit_logger.setLevel(logging.INFO)
            
            # 记录审计日志
            log_message = (
                f"操作类型={log_entry.operation_type.value} "
                f"用户ID={log_entry.user_id or 'N/A'} "
                f"IP地址={log_entry.ip_address or 'N/A'} "
                f"结果={log_entry.result.value} "
                f"资源={log_entry.resource or 'N/A'} "
                f"详情={json.dumps(log_entry.details, ensure_ascii=False)}"
            )
            
            if log_entry.result == AuditResult.FAILURE:
                audit_logger.warning(log_message)
            elif log_entry.result == AuditResult.BLOCKED:
                audit_logger.error(log_message)
            else:
                audit_logger.info(log_message)
                
        except Exception as e:
            logger.error(f"❌ 审计日志文件写入失败: {str(e)}")
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """清洗敏感信息"""
        if not self.log_sensitive_data:
            sanitized = {}
            for key, value in details.items():
                if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "...(truncated)"
                else:
                    sanitized[key] = value
            return sanitized
        return details
    
    def _get_database_url(self) -> str:
        """获取数据库连接URL"""
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'postgres')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'ai_postcard')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    async def get_audit_logs(self, 
                           user_id: Optional[str] = None,
                           operation_type: Optional[AuditOperationType] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           result: Optional[AuditResult] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """查询审计日志"""
        
        if not self.audit_enabled:
            return []
        
        try:
            # 优先使用Redis查询（性能更好）
            if self.redis_client:
                return await self._query_from_redis(
                    user_id, operation_type, start_time, end_time, result, limit, offset
                )
            
            # 回退到数据库查询
            if self.db_session:
                return await self._query_from_database(
                    user_id, operation_type, start_time, end_time, result, limit, offset
                )
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 查询审计日志失败: {str(e)}")
            return []
    
    async def _query_from_redis(self, user_id, operation_type, start_time, end_time, result, limit, offset):
        """从Redis查询审计日志"""
        try:
            # 确定查询键
            if user_id:
                query_key = f"audit_logs:user:{user_id}"
            elif operation_type:
                query_key = f"audit_logs:type:{operation_type.value}"
            elif result:
                query_key = f"audit_logs:result:{result.value}"
            else:
                query_key = "audit_logs:timeline"
            
            # 时间范围
            min_score = start_time.timestamp() if start_time else 0
            max_score = end_time.timestamp() if end_time else time.time()
            
            # 查询日志ID列表
            log_ids = self.redis_client.zrevrangebyscore(
                query_key, max_score, min_score, 
                start=offset, num=limit
            )
            
            # 获取详细日志
            logs = []
            for log_id in log_ids:
                log_key = f"audit_log:{log_id}"
                log_data = self.redis_client.hgetall(log_key)
                if log_data:
                    # 转换数据类型
                    log_data['timestamp'] = float(log_data['timestamp'])
                    if log_data.get('details'):
                        log_data['details'] = json.loads(log_data['details'])
                    logs.append(log_data)
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ Redis审计日志查询失败: {str(e)}")
            return []
    
    async def _query_from_database(self, user_id, operation_type, start_time, end_time, result, limit, offset):
        """从数据库查询审计日志"""
        try:
            query = self.db_session.query(AuditLog)
            
            # 添加过滤条件
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if operation_type:
                query = query.filter(AuditLog.operation_type == operation_type.value)
            if result:
                query = query.filter(AuditLog.result == result.value)
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            
            # 排序和分页
            query = query.order_by(AuditLog.timestamp.desc())
            query = query.offset(offset).limit(limit)
            
            # 执行查询
            results = query.all()
            
            # 转换为字典格式
            logs = []
            for audit_log in results:
                log_data = {
                    'log_id': audit_log.id,
                    'operation_type': audit_log.operation_type,
                    'user_id': audit_log.user_id,
                    'ip_address': audit_log.ip_address,
                    'user_agent': audit_log.user_agent,
                    'timestamp': audit_log.timestamp.timestamp(),
                    'result': audit_log.result,
                    'resource': audit_log.resource,
                    'details': json.loads(audit_log.details) if audit_log.details else {},
                    'session_id': audit_log.session_id,
                    'trace_id': audit_log.trace_id
                }
                logs.append(log_data)
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ 数据库审计日志查询失败: {str(e)}")
            return []
    
    async def get_audit_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取审计统计信息"""
        if not self.audit_enabled or not self.redis_client:
            return {"error": "审计日志未启用或Redis不可用"}
        
        try:
            current_time = time.time()
            stats = {
                "time_range": {"hours": hours, "end_time": current_time},
                "operations": {},
                "results": {},
                "users": {},
                "total_logs": 0
            }
            
            # 统计各小时的数据
            for i in range(hours):
                hour_timestamp = int((current_time - i * 3600) // 3600)
                stats_key = f"audit_stats:{hour_timestamp}"
                hour_stats = self.redis_client.hgetall(stats_key)
                
                for key, value in hour_stats.items():
                    count = int(value)
                    if key.startswith("count:"):
                        operation = key[6:]
                        stats["operations"][operation] = stats["operations"].get(operation, 0) + count
                        stats["total_logs"] += count
                    elif key.startswith("result:"):
                        result = key[7:]
                        stats["results"][result] = stats["results"].get(result, 0) + count
            
            # 获取活跃用户统计
            timeline_key = "audit_logs:timeline"
            start_time = current_time - hours * 3600
            recent_log_ids = self.redis_client.zrangebyscore(timeline_key, start_time, current_time)
            
            user_activity = {}
            for log_id in recent_log_ids[:1000]:  # 限制查询数量
                log_key = f"audit_log:{log_id}"
                user_id = self.redis_client.hget(log_key, "user_id")
                if user_id and user_id != "None":
                    user_activity[user_id] = user_activity.get(user_id, 0) + 1
            
            # 取前10活跃用户
            stats["users"] = dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10])
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取审计统计失败: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_old_logs(self, days: int = 90):
        """清理旧的审计日志"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            
            # 清理Redis索引
            if self.redis_client:
                self.redis_client.zremrangebyscore("audit_logs:timeline", 0, cutoff_time)
                
                # 清理操作类型索引
                for op_type in AuditOperationType:
                    type_key = f"audit_logs:type:{op_type.value}"
                    self.redis_client.zremrangebyscore(type_key, 0, cutoff_time)
                
                # 清理结果索引
                for result in AuditResult:
                    result_key = f"audit_logs:result:{result.value}"
                    self.redis_client.zremrangebyscore(result_key, 0, cutoff_time)
            
            # 清理数据库记录
            if self.db_session:
                cutoff_datetime = datetime.fromtimestamp(cutoff_time)
                self.db_session.query(AuditLog).filter(
                    AuditLog.timestamp < cutoff_datetime
                ).delete()
                self.db_session.commit()
            
            logger.info(f"✅ 已清理 {days} 天前的审计日志")
            
        except Exception as e:
            logger.error(f"❌ 清理审计日志失败: {str(e)}")
            if self.db_session:
                self.db_session.rollback()


# 全局审计日志实例
audit_service = None


def get_audit_service() -> AuditLoggingService:
    """获取全局审计服务实例"""
    global audit_service
    if not audit_service:
        audit_service = AuditLoggingService()
    return audit_service


# 装饰器版本的审计日志
def audit_operation(operation_type: AuditOperationType, resource: str = None):
    """审计操作装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            audit_svc = get_audit_service()
            start_time = time.time()
            result = AuditResult.SUCCESS
            
            try:
                # 执行原函数
                response = await func(*args, **kwargs)
                
                # 记录审计日志
                await audit_svc.log_operation(
                    operation_type=operation_type,
                    result=result,
                    resource=resource,
                    details={
                        "function": func.__name__,
                        "duration": time.time() - start_time,
                        "args_count": len(args),
                        "kwargs_count": len(kwargs)
                    }
                )
                
                return response
                
            except Exception as e:
                result = AuditResult.ERROR
                await audit_svc.log_operation(
                    operation_type=operation_type,
                    result=result,
                    resource=resource,
                    details={
                        "function": func.__name__,
                        "error": str(e),
                        "duration": time.time() - start_time
                    }
                )
                raise
        
        return wrapper
    return decorator