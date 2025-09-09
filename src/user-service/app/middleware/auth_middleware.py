# -*- coding: utf-8 -*-
"""
JWT身份验证中间件
实现全局身份验证和向后兼容机制
"""

import os
import json
import uuid
import logging
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService, CurrentUser
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """身份验证异常"""
    pass


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT身份验证中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
        
        # 配置选项
        # 默认强制Token，符合设计要求（可通过环境变量放宽，仅用于开发）
        self.legacy_mode = os.getenv('SECURITY_LEGACY_MODE', 'false').lower() == 'true'
        self.strict_mode = os.getenv('SECURITY_STRICT_MODE', 'true').lower() == 'true'
        self.jwt_required = os.getenv('JWT_REQUIRED', 'true').lower() == 'true'
        
        # 排除路径（不需要认证）
        self.excluded_paths = {
            "/health", "/docs", "/openapi.json", "/redoc",
            "/api/v1/health", "/api/v1/docs"
        }
        
        # 公开API路径（允许匿名访问）
        # 公开API路径（默认仅登录与刷新允许匿名，分享页需要签名可选，默认要求登录）
        self.public_paths = {
            "/api/v1/miniprogram/auth/login",
            "/api/v1/miniprogram/auth/refresh",
        }
        
        logger.info(f"🔐 认证中间件初始化: legacy_mode={self.legacy_mode}, strict_mode={self.strict_mode}")
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 检查是否为排除路径
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 检查是否为公开路径
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        try:
            # 执行身份验证
            auth_result = await self._authenticate_request(request)
            
            if auth_result.success and auth_result.user:
                # 注入用户信息到请求上下文
                request.state.user = CurrentUser(
                    user_id=auth_result.user["id"],
                    openid=auth_result.user.get("openid", ""),
                    role=auth_result.user.get("role", "user"),
                    permissions=set(self.auth_service._get_user_permissions(
                        auth_result.user.get("role", "user")
                    )),
                    session_id=auth_result.session_id
                )
                
                # 添加认证信息到请求头（用于下游服务）
                request.headers.__dict__.setdefault("_list", []).append(
                    (b"x-authenticated-user", auth_result.user["id"].encode())
                )
                
                logger.debug(f"✅ 用户认证成功: {auth_result.user['id']}")
            
            response = await call_next(request)
            return response
            
        except AuthenticationError as e:
            logger.warning(f"❌ 身份验证失败: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={
                    "code": -401,
                    "message": f"身份验证失败: {str(e)}",
                    "data": None
                }
            )
        except Exception as e:
            logger.error(f"💥 认证中间件异常: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "code": -500,
                    "message": "内部服务器错误",
                    "data": None
                }
            )
    
    async def _authenticate_request(self, request: Request):
        """认证请求"""
        
        # 严格安全模式（目标状态）
        if self.strict_mode:
            return await self._jwt_authenticate(request)
        
        # 兼容模式（迁移状态）
        if self.legacy_mode:
            return await self._hybrid_authenticate(request)
        
        # 传统模式（当前状态）
        return await self._legacy_authenticate(request)
    
    async def _hybrid_authenticate(self, request: Request):
        """混合认证：优先JWT，降级到user_id"""
        
        # 优先尝试JWT认证
        jwt_result = await self._try_jwt_authenticate(request)
        if jwt_result.success:
            return jwt_result
        
        # 如果JWT认证失败但要求强制使用JWT
        if self.jwt_required:
            raise AuthenticationError("需要有效的JWT Token")
        
        # 降级到传统user_id认证
        legacy_result = await self._legacy_authenticate(request)
        if legacy_result.success:
            # 为传统用户创建临时会话
            await self._create_temp_session(legacy_result.user)
        
        return legacy_result
    
    async def _jwt_authenticate(self, request: Request):
        """JWT认证"""
        try:
            # 提取Token
            token = self._extract_token(request)
            if not token:
                raise AuthenticationError("缺少身份验证令牌")
            
            # 验证Token
            payload = await self.auth_service.verify_token(token)
            
            # 获取用户信息
            user_data = await self._get_user_by_id(payload["user_id"])
            if not user_data:
                raise AuthenticationError("用户不存在")
            
            from app.services.auth_service import AuthResult
            return AuthResult(
                success=True,
                user=user_data,
                session_id=payload.get("session_id"),
                message="JWT认证成功"
            )
            
        except HTTPException as e:
            raise AuthenticationError(e.detail)
        except Exception as e:
            raise AuthenticationError(f"JWT认证失败: {str(e)}")
    
    async def _try_jwt_authenticate(self, request: Request):
        """尝试JWT认证（不抛出异常）"""
        try:
            return await self._jwt_authenticate(request)
        except AuthenticationError:
            from app.services.auth_service import AuthResult
            return AuthResult(success=False, message="JWT认证失败")
    
    async def _legacy_authenticate(self, request: Request):
        """传统user_id认证"""
        try:
            # 解析用户身份
            user_data = await self._resolve_user_identity(request)
            if not user_data:
                raise AuthenticationError("无法识别用户身份")
            
            from app.services.auth_service import AuthResult
            return AuthResult(
                success=True,
                user=user_data,
                message="传统认证成功"
            )
            
        except Exception as e:
            raise AuthenticationError(f"用户身份解析失败: {str(e)}")
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """提取JWT Token"""
        # 从Authorization头提取
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 从X-Access-Token头提取（备选）
        token = request.headers.get("x-access-token")
        if token:
            return token
        
        return None
    
    async def _resolve_user_identity(self, request: Request) -> Optional[dict]:
        """解析用户身份（兼容多种方式）"""
        user_id = None
        
        # 优先级1: 请求头中的user_id（兼容旧客户端）
        user_id = request.headers.get('x-user-id')
        if user_id:
            logger.debug(f"从X-User-ID头获取用户ID: {user_id}")
        
        # 优先级2: 查询参数中的user_id
        if not user_id:
            user_id = request.query_params.get('user_id')
            if user_id:
                logger.debug(f"从查询参数获取用户ID: {user_id}")
        
        # 优先级3: 请求体中的user_id
        if not user_id and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await self._get_request_body(request)
                if body and isinstance(body, dict) and 'user_id' in body:
                    user_id = body['user_id']
                    logger.debug(f"从请求体获取用户ID: {user_id}")
            except Exception as e:
                logger.warning(f"解析请求体失败: {str(e)}")
        
        if user_id:
            return await self._get_user_by_id(user_id)
        
        return None
    
    async def _get_request_body(self, request: Request) -> Optional[dict]:
        """安全地获取请求体"""
        try:
            if hasattr(request, '_body'):
                body = request._body
            else:
                body = await request.body()
                request._body = body  # 缓存body
            
            if body:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    return json.loads(body.decode())
        except Exception as e:
            logger.warning(f"解析请求体异常: {str(e)}")
        
        return None
    
    async def _get_user_by_id(self, user_id: str) -> Optional[dict]:
        """根据用户ID获取用户信息"""
        try:
            # 获取数据库会话
            db = next(get_db())
            
            # 查询用户
            # 兼容字符串与UUID类型
            try:
                user_uuid = uuid.UUID(str(user_id))
            except Exception:
                user_uuid = user_id  # 回退到原值，避免因异常中断
            user = db.query(User).filter(User.id == user_uuid).first()
            if user:
                return {
                    "id": user.id,
                    "openid": user.openid,
                    "nickname": user.nickname,
                    "avatar": user.avatar_url,
                    "role": getattr(user, 'role', 'user'),
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
        
        return None
    
    async def _create_temp_session(self, user_data: dict):
        """为传统用户创建临时会话"""
        try:
            # 创建临时会话标识
            import uuid
            temp_session_id = f"legacy_{uuid.uuid4()}"
            
            # 缓存临时会话
            await self.auth_service.redis.setex(
                f"temp_session:{temp_session_id}",
                3600,  # 1小时过期
                json.dumps(user_data)
            )
            
            logger.debug(f"为用户 {user_data['id']} 创建临时会话: {temp_session_id}")
            
        except Exception as e:
            logger.warning(f"创建临时会话失败: {str(e)}")
    
    def _is_excluded_path(self, path: str) -> bool:
        """检查是否为排除路径"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径"""
        return path in self.public_paths


# FastAPI依赖注入函数
async def get_current_user(request: Request) -> CurrentUser:
    """获取当前用户（FastAPI依赖注入）"""
    if not hasattr(request.state, 'user'):
        raise HTTPException(status_code=401, detail="未认证的用户")
    
    return request.state.user


async def require_authentication(request: Request) -> CurrentUser:
    """要求用户认证（FastAPI依赖注入）"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="需要用户认证")
    
    return user
