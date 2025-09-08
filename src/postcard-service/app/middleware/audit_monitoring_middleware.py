# -*- coding: utf-8 -*-
"""
审计监控中间件
集成审计日志和实时监控功能
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

from ..services.audit_logging_service import (
    AuditLoggingService, AuditOperationType, AuditResult, get_audit_service
)
from ..services.monitoring_service import (
    MonitoringService, MetricValue, MetricType, get_monitoring_service
)

logger = logging.getLogger(__name__)


class AuditMonitoringMiddleware(BaseHTTPMiddleware):
    """审计监控中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_service = get_audit_service()
        self.monitoring_service = get_monitoring_service()
        
        # 配置
        self.audit_enabled = True
        self.monitoring_enabled = True
        
        logger.info("📋 审计监控中间件初始化完成")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件主处理函数"""
        start_time = time.time()
        trace_id = str(uuid.uuid4())[:8]
        
        # 提取请求信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        endpoint = f"{request.method} {request.url.path}"
        user_id = await self._extract_user_id(request)
        session_id = await self._extract_session_id(request)
        
        # 在请求状态中保存trace_id
        request.state.trace_id = trace_id
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算响应时间
            response_time = time.time() - start_time
            success = 200 <= response.status_code < 400
            
            # 记录审计日志
            if self.audit_enabled:
                await self._log_request_audit(
                    request, response, user_id, client_ip, user_agent,
                    response_time, success, trace_id, session_id
                )
            
            # 记录监控指标
            if self.monitoring_enabled:
                await self._record_monitoring_metrics(
                    request, response, response_time, success
                )
            
            # 添加审计头部
            self._add_audit_headers(response, trace_id)
            
            return response
            
        except Exception as e:
            # 记录异常审计日志
            response_time = time.time() - start_time
            
            if self.audit_enabled:
                await self.audit_service.log_operation(
                    operation_type=AuditOperationType.SECURITY_EVENT,
                    user_id=user_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    result=AuditResult.ERROR,
                    resource=endpoint,
                    details={
                        "error": str(e),
                        "response_time": response_time,
                        "exception_type": type(e).__name__
                    },
                    session_id=session_id,
                    trace_id=trace_id
                )
            
            # 记录错误指标
            if self.monitoring_enabled:
                await self._record_error_metrics(endpoint, str(e))
            
            raise
    
    async def _log_request_audit(self, request: Request, response: Response, 
                               user_id: str, client_ip: str, user_agent: str,
                               response_time: float, success: bool, 
                               trace_id: str, session_id: str):
        """记录请求审计日志"""
        try:
            # 确定操作类型
            operation_type = self._determine_operation_type(request)
            
            # 确定审计结果
            if success:
                result = AuditResult.SUCCESS
            elif response.status_code == 403:
                result = AuditResult.BLOCKED  
            elif response.status_code >= 400:
                result = AuditResult.FAILURE
            else:
                result = AuditResult.SUCCESS
            
            # 构建详情信息
            details = {
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "response_time": response_time,
                "content_length": response.headers.get("content-length", "0"),
                "referer": request.headers.get("referer", ""),
            }
            
            # 敏感操作记录更多信息
            if operation_type in [AuditOperationType.USER_LOGIN, 
                                 AuditOperationType.POSTCARD_CREATE,
                                 AuditOperationType.ADMIN_OPERATION]:
                # 记录请求体大小（不记录内容以保护隐私）
                if hasattr(request.state, 'body_size'):
                    details["request_body_size"] = request.state.body_size
            
            # 记录审计日志
            await self.audit_service.log_operation(
                operation_type=operation_type,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                result=result,
                resource=str(request.url.path),
                details=details,
                session_id=session_id,
                trace_id=trace_id
            )
            
        except Exception as e:
            logger.error(f"❌ 记录审计日志失败: {str(e)}")
    
    async def _record_monitoring_metrics(self, request: Request, response: Response,
                                       response_time: float, success: bool):
        """记录监控指标"""
        try:
            current_time = time.time()
            
            # 记录请求计数
            await self._record_metric(MetricValue(
                MetricType.REQUEST_COUNT, 1, current_time,
                labels={"method": request.method, "endpoint": str(request.url.path)}
            ))
            
            # 记录响应时间（毫秒）
            response_time_ms = response_time * 1000
            await self._record_metric(MetricValue(
                MetricType.RESPONSE_TIME, response_time_ms, current_time,
                labels={"endpoint": str(request.url.path)}
            ))
            
            # 记录错误率
            if not success:
                await self._record_metric(MetricValue(
                    MetricType.ERROR_RATE, 1, current_time,
                    labels={"status_code": str(response.status_code)}
                ))
            
        except Exception as e:
            logger.error(f"❌ 记录监控指标失败: {str(e)}")
    
    async def _record_error_metrics(self, endpoint: str, error: str):
        """记录错误指标"""
        try:
            current_time = time.time()
            await self._record_metric(MetricValue(
                MetricType.ERROR_RATE, 1, current_time,
                labels={"endpoint": endpoint, "error": error[:100]}
            ))
        except Exception as e:
            logger.error(f"❌ 记录错误指标失败: {str(e)}")
    
    async def _record_metric(self, metric: MetricValue):
        """记录指标（简化版本，直接调用监控服务）"""
        # 这里简化实现，实际可以缓存后批量发送
        pass  # 监控服务会通过定时任务收集系统指标
    
    def _determine_operation_type(self, request: Request) -> AuditOperationType:
        """确定操作类型"""
        path = request.url.path.lower()
        method = request.method.upper()
        
        # 用户操作
        if "login" in path:
            return AuditOperationType.USER_LOGIN
        elif "logout" in path:
            return AuditOperationType.USER_LOGOUT
        elif "register" in path:
            return AuditOperationType.USER_REGISTER
        
        # 明信片操作
        elif "postcard" in path or "create" in path:
            if method == "POST":
                return AuditOperationType.POSTCARD_CREATE
            elif method == "DELETE":
                return AuditOperationType.POSTCARD_DELETE
            elif method == "GET":
                return AuditOperationType.POSTCARD_VIEW
        
        # 配额操作
        elif "quota" in path:
            return AuditOperationType.QUOTA_CONSUME
        
        # 管理操作
        elif "admin" in path:
            return AuditOperationType.ADMIN_OPERATION
        
        # 数据访问
        elif method == "GET":
            return AuditOperationType.DATA_ACCESS
        
        # 默认为数据访问
        return AuditOperationType.DATA_ACCESS
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """提取用户ID"""
        try:
            # 从认证中间件设置的用户信息中获取
            current_user = getattr(request.state, 'current_user', None)
            if current_user:
                return getattr(current_user, 'user_id', None)
            
            # 从请求参数中获取（备用方案）
            return request.query_params.get("user_id")
            
        except Exception:
            return None
    
    async def _extract_session_id(self, request: Request) -> Optional[str]:
        """提取会话ID"""
        try:
            # 从Cookie或Header中获取会话ID
            session_id = request.cookies.get("session_id")
            if not session_id:
                session_id = request.headers.get("X-Session-ID")
            
            return session_id
            
        except Exception:
            return None
    
    def _add_audit_headers(self, response: Response, trace_id: str):
        """添加审计相关响应头"""
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Audit-Enabled"] = "true"
        response.headers["X-Monitoring-Enabled"] = "true"


class AuditContext:
    """审计上下文管理器"""
    
    def __init__(self, operation_type: AuditOperationType, 
                 user_id: Optional[str] = None,
                 resource: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.operation_type = operation_type
        self.user_id = user_id
        self.resource = resource
        self.details = details or {}
        self.start_time = None
        self.audit_service = get_audit_service()
    
    async def __aenter__(self):
        """进入审计上下文"""
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出审计上下文"""
        duration = time.time() - self.start_time
        self.details.update({"duration": duration})
        
        if exc_type is None:
            result = AuditResult.SUCCESS
        else:
            result = AuditResult.ERROR
            self.details.update({
                "error": str(exc_val),
                "exception_type": exc_type.__name__
            })
        
        await self.audit_service.log_operation(
            operation_type=self.operation_type,
            user_id=self.user_id,
            result=result,
            resource=self.resource,
            details=self.details
        )


def audit_operation(operation_type: AuditOperationType, 
                   resource: Optional[str] = None,
                   extract_user_id: bool = True):
    """审计操作装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取用户ID（如果需要）
            user_id = None
            if extract_user_id:
                for arg in args:
                    if hasattr(arg, 'user_id'):
                        user_id = arg.user_id
                        break
                if not user_id:
                    user_id = kwargs.get('user_id')
            
            # 使用审计上下文
            async with AuditContext(
                operation_type=operation_type,
                user_id=user_id,
                resource=resource,
                details={
                    "function": func.__name__,
                    "module": func.__module__
                }
            ):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# 审计日志查询API辅助函数
async def get_audit_dashboard(hours: int = 24) -> Dict[str, Any]:
    """获取审计仪表板数据"""
    try:
        audit_service = get_audit_service()
        monitoring_service = get_monitoring_service()
        
        dashboard = {
            "time_range": {"hours": hours},
            "audit": {},
            "monitoring": {},
            "system": {}
        }
        
        # 获取审计统计
        audit_stats = await audit_service.get_audit_statistics(hours)
        dashboard["audit"] = audit_stats
        
        # 获取监控数据
        system_health = await monitoring_service.get_system_health()
        dashboard["monitoring"] = system_health
        
        # 获取最近告警
        recent_alerts = await monitoring_service.get_alerts(hours=hours, limit=10)
        dashboard["monitoring"]["recent_alerts"] = recent_alerts
        
        return dashboard
        
    except Exception as e:
        logger.error(f"❌ 获取审计仪表板失败: {str(e)}")
        return {"error": str(e)}


async def search_audit_logs(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """搜索审计日志"""
    try:
        audit_service = get_audit_service()
        
        # 解析过滤条件
        user_id = filters.get('user_id')
        operation_type = None
        if filters.get('operation_type'):
            try:
                operation_type = AuditOperationType(filters['operation_type'])
            except ValueError:
                pass
        
        start_time = filters.get('start_time')
        end_time = filters.get('end_time')
        result = None
        if filters.get('result'):
            try:
                result = AuditResult(filters['result'])
            except ValueError:
                pass
        
        limit = min(filters.get('limit', 100), 1000)  # 最大1000条
        offset = filters.get('offset', 0)
        
        # 执行查询
        logs = await audit_service.get_audit_logs(
            user_id=user_id,
            operation_type=operation_type,
            start_time=start_time,
            end_time=end_time,
            result=result,
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except Exception as e:
        logger.error(f"❌ 搜索审计日志失败: {str(e)}")
        return []
