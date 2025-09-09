# -*- coding: utf-8 -*-
"""
API安全中间件
整合输入验证、限流、安全监控等安全机制
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import asyncio

from ..services.input_validation_service import InputValidationService, RequestValidationMiddleware
from ..services.rate_limiting_service import RateLimitingService
from ..services.security_monitoring_service import (
    SecurityMonitoringService, SecurityEvent, SecurityEventType, ThreatLevel
)

logger = logging.getLogger(__name__)


class APISecurityMiddleware(BaseHTTPMiddleware):
    """API安全中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.input_validator = InputValidationService()
        self.request_validator = RequestValidationMiddleware()
        self.rate_limiter = RateLimitingService()
        self.security_monitor = SecurityMonitoringService()
        
        # 安全配置
        self.security_enabled = True
        self.strict_mode = False  # 严格模式：发生任何安全问题都拒绝请求
        
        logger.info("🔒 API安全中间件初始化完成")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件主处理函数"""
        start_time = time.time()
        
        # 提取请求信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        endpoint = f"{request.method} {request.url.path}"
        user_id = await self._extract_user_id(request)
        
        # 安全检查结果
        security_result = {
            "allowed": True,
            "warnings": [],
            "errors": [],
            "blocked_reasons": []
        }
        
        try:
            # 1. 增加并发计数
            concurrent_count = await self.rate_limiter.increment_concurrent_requests()
            
            # 2. 限流检查（对低风险查询类接口放宽/跳过）
            action = self._get_action_from_endpoint(endpoint)
            skip_rate_limit = action in {"query_quota"}

            rate_limit_result = {"allowed": True}
            if not skip_rate_limit:
                rate_limit_result = await self.rate_limiter.check_rate_limit(
                    user_id=user_id,
                    ip_address=client_ip,
                    endpoint=endpoint,
                    action=action
                )
            
            if not rate_limit_result["allowed"]:
                security_result["allowed"] = False
                security_result["blocked_reasons"].extend(rate_limit_result["blocked_by"])
                
                # 记录限流事件
                await self.security_monitor.record_security_event(
                    SecurityEvent(
                        event_id="",
                        event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                        threat_level=ThreatLevel.MEDIUM,
                        user_id=user_id,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        endpoint=endpoint,
                        timestamp=time.time(),
                        description=f"限流触发: {', '.join(rate_limit_result['blocked_by'])}",
                        metadata={
                            "blocked_by": rate_limit_result["blocked_by"],
                            "retry_after": rate_limit_result["retry_after"],
                            "limits": rate_limit_result["limits"]
                        }
                    )
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": "请求过于频繁，请稍后重试",
                        "details": {
                            "retry_after": rate_limit_result["retry_after"],
                            "blocked_by": rate_limit_result["blocked_by"]
                        }
                    },
                    headers={
                        "Retry-After": str(int(rate_limit_result["retry_after"])),
                        "X-RateLimit-Limit": str(rate_limit_result.get("limits", {}).get("global", {}).get("limit", "unknown")),
                        "X-RateLimit-Remaining": str(rate_limit_result.get("remaining", {}).get("global", 0))
                    }
                )
            
            # 3. 输入验证（对于POST/PUT请求）
            if request.method in ["POST", "PUT", "PATCH"]:
                input_validation_result = await self._validate_request_input(request, user_id, client_ip)
                
                if not input_validation_result["allowed"]:
                    security_result["allowed"] = False
                    security_result["errors"].extend(input_validation_result["errors"])
                    
                    return JSONResponse(
                        status_code=400,
                        content={
                            "code": 400,
                            "message": "输入验证失败",
                            "details": {
                                "errors": input_validation_result["errors"],
                                "warnings": input_validation_result.get("warnings", [])
                            }
                        }
                    )
                
                security_result["warnings"].extend(input_validation_result.get("warnings", []))
            
            # 4. 可疑行为检测
            suspicious_event = await self.security_monitor.detect_suspicious_behavior(
                user_id, client_ip, user_agent, endpoint
            )
            
            if suspicious_event:
                await self.security_monitor.record_security_event(suspicious_event)
                
                if self.strict_mode and suspicious_event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "code": 403,
                            "message": "检测到可疑行为，请求被拒绝",
                            "details": {"reason": "suspicious_behavior"}
                        }
                    )
            
            # 5. 处理请求
            response = await call_next(request)
            
            # 6. 记录请求结果
            success = 200 <= response.status_code < 400
            response_time = time.time() - start_time
            
            await self.rate_limiter.record_request_result(success, response_time, response.status_code)
            
            # 7. 添加安全响应头
            self._add_security_headers(response)
            
            # 8. 记录安全日志
            if security_result["warnings"] or not success:
                logger.info(f"🔍 安全检查完成: user_id={user_id}, ip={client_ip}, "
                           f"endpoint={endpoint}, success={success}, warnings={len(security_result['warnings'])}")
            
            return response
            
        except Exception as e:
            # 记录异常
            logger.error(f"❌ API安全中间件处理异常: {str(e)}")
            
            # 记录安全事件
            await self.security_monitor.record_security_event(
                SecurityEvent(
                    event_id="",
                    event_type=SecurityEventType.SUSPICIOUS_BEHAVIOR,
                    threat_level=ThreatLevel.LOW,
                    user_id=user_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    timestamp=time.time(),
                    description=f"API安全中间件异常: {str(e)}",
                    metadata={"error": str(e), "exception_type": type(e).__name__}
                )
            )
            
            # 继续处理请求，不因安全检查异常而中断服务
            response = await call_next(request)
            return response
            
        finally:
            # 减少并发计数
            await self.rate_limiter.decrement_concurrent_requests()
    
    async def _validate_request_input(self, request: Request, user_id: str, client_ip: str) -> Dict[str, Any]:
        """验证请求输入"""
        result = {
            "allowed": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 获取请求体
            body = await request.body()
            if not body:
                return result
            
            # 解析JSON
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                result["allowed"] = False
                result["errors"].append("请求体不是有效的JSON格式")
                return result
            
            # 针对不同端点进行验证
            if "create" in request.url.path:
                # 明信片创建请求验证
                validation_result = await self.request_validator.validate_postcard_request(request_data)
                
                if not validation_result["is_valid"]:
                    result["allowed"] = False
                    result["errors"] = validation_result["errors"]
                    
                    # 记录恶意输入事件
                    malicious_event = await self.security_monitor.detect_malicious_input(
                        user_id, str(request_data), client_ip
                    )
                    if malicious_event:
                        await self.security_monitor.record_security_event(malicious_event)
                
                result["warnings"] = validation_result.get("warnings", [])
            
            # 通用输入长度检查
            if self._check_input_size_limits(request_data):
                result["warnings"].append("输入数据较大，已进行安全检查")
            
        except Exception as e:
            logger.error(f"❌ 请求输入验证失败: {str(e)}")
            result["allowed"] = False
            result["errors"].append("输入验证过程出现错误")
        
        return result
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（可能有多个代理）
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 回退到直连IP
        return request.client.host if request.client else "unknown"
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """提取用户ID"""
        try:
            # 从认证中间件设置的用户信息中获取
            current_user = getattr(request.state, 'current_user', None)
            if current_user:
                return getattr(current_user, 'user_id', None)
            # 简化版认证中间件注入的字段
            user_id_from_state = getattr(request.state, 'user_id', None)
            if user_id_from_state:
                return user_id_from_state
            
            # 从请求体中提取（临时方案）
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        return data.get("user_id")
                    except:
                        pass
            
            # 从查询参数中提取
            return request.query_params.get("user_id")
            
        except Exception as e:
            logger.debug(f"提取用户ID失败: {str(e)}")
            return None
    
    def _get_action_from_endpoint(self, endpoint: str) -> str:
        """从端点推断动作类型"""
        ep = endpoint.lower()
        # 拆分方法与路径，例如 "GET /api/..."
        try:
            method, path = ep.split(" ", 1)
        except ValueError:
            method, path = "get", ep
        
        # 优先匹配更具体的任务端点
        if "/postcards/status" in path:
            return "task_status"
        if "/postcards/result" in path:
            return "task_result"
        
        # 登录与配额
        if "/auth/login" in path:
            return "login"
        if "/users/" in path and "/quota" in path:
            return "query_quota"
        
        # 创建明信片：必须是 POST 方法，或明确的 /postcards/create
        if method == "post" and "/postcards" in path:
            return "create_postcard"
        if "/postcards/create" in path:
            return "create_postcard"
        
        # 列表/查询类
        if "/postcards/user" in path or "/postcards" in path or "list" in path:
            return "list_postcards"
        
        return "default"
    
    def _check_input_size_limits(self, data: Any) -> bool:
        """检查输入大小限制"""
        try:
            data_str = json.dumps(data) if not isinstance(data, str) else data
            return len(data_str) > 10000  # 10KB阈值
        except:
            return False
    
    def _add_security_headers(self, response: Response):
        """添加安全响应头"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "X-API-Security": "enabled",
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


# 装饰器版本的安全检查
def require_security_check(
    validate_input: bool = True,
    check_rate_limit: bool = True,
    monitor_behavior: bool = True
):
    """安全检查装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以实现装饰器版本的安全检查
            # 暂时直接调用原函数
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class SecurityConfig:
    """安全配置类"""
    
    def __init__(self):
        import os
        
        # 基础安全开关
        self.security_enabled = os.getenv('API_SECURITY_ENABLED', 'true').lower() == 'true'
        self.strict_mode = os.getenv('API_SECURITY_STRICT_MODE', 'false').lower() == 'true'
        
        # 输入验证配置
        self.input_validation_enabled = os.getenv('INPUT_VALIDATION_ENABLED', 'true').lower() == 'true'
        self.max_input_size = int(os.getenv('MAX_INPUT_SIZE', '10240'))  # 10KB
        
        # 限流配置
        self.rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED', 'true').lower() == 'true'
        self.global_rate_limit = int(os.getenv('GLOBAL_RATE_LIMIT', '10000'))
        
        # 监控配置
        self.security_monitoring_enabled = os.getenv('SECURITY_MONITORING_ENABLED', 'true').lower() == 'true'
        self.alert_webhook_url = os.getenv('SECURITY_ALERT_WEBHOOK_URL', '')
        
        # 日志配置
        self.security_log_level = os.getenv('SECURITY_LOG_LEVEL', 'INFO')
        self.log_sensitive_data = os.getenv('LOG_SENSITIVE_DATA', 'false').lower() == 'true'
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            "security_enabled": self.security_enabled,
            "strict_mode": self.strict_mode,
            "input_validation_enabled": self.input_validation_enabled,
            "max_input_size": self.max_input_size,
            "rate_limiting_enabled": self.rate_limiting_enabled,
            "global_rate_limit": self.global_rate_limit,
            "security_monitoring_enabled": self.security_monitoring_enabled,
            "security_log_level": self.security_log_level,
            "log_sensitive_data": self.log_sensitive_data
        }
