# -*- coding: utf-8 -*-
"""
JWT身份验证服务
实现Token生成、验证、刷新和撤销功能
"""

import os
import jwt
import uuid
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from pydantic import BaseModel
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT Token载荷结构"""
    user_id: str
    openid: str
    role: str = "user"
    permissions: list[str] = []
    exp: int
    iat: int
    jti: str
    session_id: Optional[str] = None


class AuthResult(BaseModel):
    """认证结果"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_id: Optional[str] = None
    expires_in: int = 7 * 24 * 3600
    message: str = ""


class AuthService:
    """JWT身份验证服务"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "ai-postcard-secret-key-2025")
        self.algorithm = "HS256"
        self.access_token_expire = 7 * 24 * 3600  # 7天
        self.refresh_token_expire = 30 * 24 * 3600  # 30天
        
        # Redis连接用于Token缓存和撤销控制
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # 异步Redis客户端，返回字符串
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # 基础权限定义
        self.base_permissions = {
            "user": [
                "postcard:create", "postcard:read", "postcard:delete",
                "quota:read", "user:read", "user:update"
            ],
            "premium_user": [
                "postcard:create", "postcard:read", "postcard:delete",
                "quota:read", "user:read", "user:update",
                "premium:access", "advanced:features"
            ],
            "admin": [
                "postcard:create", "postcard:read", "postcard:delete", "postcard:manage",
                "quota:read", "quota:manage", "user:read", "user:update", "user:manage",
                "admin:access", "system:manage"
            ]
        }
    
    async def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        try:
            now = datetime.utcnow()
            session_id = str(uuid.uuid4())
            jti = str(uuid.uuid4())
            
            payload = {
                "user_id": user_data["id"],
                "openid": user_data.get("openid", ""),
                "role": user_data.get("role", "user"),
                "permissions": self._get_user_permissions(user_data.get("role", "user")),
                "exp": int((now + timedelta(seconds=self.access_token_expire)).timestamp()),
                "iat": int(now.timestamp()),
                "jti": jti,
                "session_id": session_id
            }
            
            # 缓存Token用于撤销控制
            await self._cache_token(jti, user_data["id"], session_id)
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"✅ JWT Token创建成功: 用户 {user_data['id']}, JTI: {jti}")
            
            return token
            
        except Exception as e:
            logger.error(f"❌ JWT Token创建失败: {str(e)}")
            raise HTTPException(status_code=500, detail="Token创建失败")
    
    async def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        try:
            now = datetime.utcnow()
            jti = str(uuid.uuid4())
            
            payload = {
                "user_id": user_id,
                "type": "refresh",
                "exp": int((now + timedelta(seconds=self.refresh_token_expire)).timestamp()),
                "iat": int(now.timestamp()),
                "jti": jti
            }
            
            # 缓存刷新Token
            await self._cache_refresh_token(jti, user_id)
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"✅ 刷新Token创建成功: 用户 {user_id}, JTI: {jti}")
            
            return token
            
        except Exception as e:
            logger.error(f"❌ 刷新Token创建失败: {str(e)}")
            raise HTTPException(status_code=500, detail="刷新Token创建失败")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """验证访问令牌"""
        try:
            # 解码Token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查Token是否被撤销
            if await self.is_token_revoked(payload["jti"]):
                raise HTTPException(status_code=401, detail="Token已失效")
            
            # 检查过期时间
            if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Token已过期")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT Token已过期")
            raise HTTPException(status_code=401, detail="Token已过期")
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的JWT Token: {str(e)}")
            raise HTTPException(status_code=401, detail="无效的Token")
        except Exception as e:
            logger.error(f"Token验证失败: {str(e)}")
            raise HTTPException(status_code=401, detail="Token验证失败")
    
    async def refresh_access_token(self, refresh_token: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            # 验证刷新Token
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="无效的刷新Token")
            
            # 检查是否被撤销
            if await self.is_refresh_token_revoked(payload["jti"]):
                raise HTTPException(status_code=401, detail="刷新Token已失效")
            
            user_id = payload["user_id"]
            
            # 获取用户信息（这里需要从数据库获取最新的用户信息）
            user_data = await self._get_user_data(user_id)
            if not user_data:
                raise HTTPException(status_code=401, detail="用户不存在")
            
            # 生成新的访问Token
            new_access_token = await self.create_access_token(user_data)
            new_refresh_token = await self.create_refresh_token(user_id)
            
            # 撤销旧的刷新Token
            await self.revoke_refresh_token(payload["jti"])
            
            logger.info(f"✅ Token刷新成功: 用户 {user_id}")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": self.access_token_expire,
                "user": user_data
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="刷新Token已过期")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="无效的刷新Token")
        except Exception as e:
            logger.error(f"Token刷新失败: {str(e)}")
            raise HTTPException(status_code=401, detail="Token刷新失败")
    
    async def revoke_token(self, jti: str) -> bool:
        """撤销访问令牌"""
        try:
            # 将Token JTI添加到黑名单
            await self.redis.setex(f"revoked_token:{jti}", self.access_token_expire, "1")
            logger.info(f"✅ Token已撤销: JTI {jti}")
            return True
        except Exception as e:
            logger.error(f"❌ Token撤销失败: {str(e)}")
            return False
    
    async def revoke_refresh_token(self, jti: str) -> bool:
        """撤销刷新令牌"""
        try:
            await self.redis.setex(f"revoked_refresh_token:{jti}", self.refresh_token_expire, "1")
            logger.info(f"✅ 刷新Token已撤销: JTI {jti}")
            return True
        except Exception as e:
            logger.error(f"❌ 刷新Token撤销失败: {str(e)}")
            return False
    
    async def revoke_user_tokens(self, user_id: str) -> bool:
        """撤销用户的所有Token"""
        try:
            # 获取用户所有有效的Token
            pattern = f"user_token:{user_id}:*"
            keys = await self.redis.keys(pattern)
            
            if keys:
                # 批量撤销
                for key in keys:
                    jti = str(key).split(":")[-1]
                    await self.revoke_token(jti)
            
            logger.info(f"✅ 用户所有Token已撤销: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 撤销用户Token失败: {str(e)}")
            return False
    
    async def is_token_revoked(self, jti: str) -> bool:
        """检查Token是否被撤销"""
        try:
            result = await self.redis.get(f"revoked_token:{jti}")
            return result is not None
        except Exception as e:
            logger.error(f"检查Token撤销状态失败: {str(e)}")
            return False
    
    async def is_refresh_token_revoked(self, jti: str) -> bool:
        """检查刷新Token是否被撤销"""
        try:
            result = await self.redis.get(f"revoked_refresh_token:{jti}")
            return result is not None
        except Exception as e:
            logger.error(f"检查刷新Token撤销状态失败: {str(e)}")
            return False
    
    def _get_user_permissions(self, role: str) -> list[str]:
        """获取用户权限列表"""
        return self.base_permissions.get(role, self.base_permissions["user"])
    
    async def _cache_token(self, jti: str, user_id: str, session_id: str):
        """缓存Token信息"""
        try:
            token_key = f"user_token:{user_id}:{jti}"
            session_key = f"user_session:{session_id}"
            
            token_data = {
                "jti": jti,
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # 存储Token映射
            await self.redis.setex(token_key, self.access_token_expire, str(token_data))
            
            # 存储会话映射
            await self.redis.setex(session_key, self.access_token_expire, user_id)
            
        except Exception as e:
            logger.error(f"缓存Token失败: {str(e)}")
    
    async def _cache_refresh_token(self, jti: str, user_id: str):
        """缓存刷新Token信息"""
        try:
            key = f"user_refresh_token:{user_id}:{jti}"
            data = {
                "jti": jti,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            await self.redis.setex(key, self.refresh_token_expire, str(data))
        except Exception as e:
            logger.error(f"缓存刷新Token失败: {str(e)}")
    
    async def _get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户数据（需要实现数据库查询）"""
        # 这里应该从数据库获取用户信息
        # 暂时返回模拟数据，实际实现时需要连接数据库
        return {
            "id": user_id,
            "openid": f"openid_{user_id}",
            "role": "user",
            "nickname": "用户",
            "avatar": ""
        }


class CurrentUser(BaseModel):
    """当前用户信息"""
    user_id: str
    openid: str
    role: str
    permissions: Set[str]
    session_id: Optional[str] = None
    
    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: list[str]) -> bool:
        """检查用户是否有任一权限"""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: list[str]) -> bool:
        """检查用户是否有所有权限"""
        return all(perm in self.permissions for perm in permissions)
