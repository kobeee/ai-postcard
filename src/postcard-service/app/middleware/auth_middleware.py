# -*- coding: utf-8 -*-
"""
JWT身份验证中间件（Postcard Service）
强制要求所有业务接口需携带有效的JWT访问令牌（健康与文档除外）
"""

import os
import logging
from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "ai-postcard-secret-key-2025")
        self.jwt_alg = "HS256"
        self.excluded_paths = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.excluded_paths or path.startswith("/docs"):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return JSONResponse(status_code=401, content={
                "code": -401,
                "message": "缺少身份验证令牌",
                "data": None,
            })

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_alg])
            # 简单注入 user_id 到请求上下文，方便下游获取
            request.state.user_id = payload.get("user_id")
            request.state.user_role = payload.get("role", "user")
            request.state.session_id = payload.get("session_id")
        except JWTError as e:
            logger.warning(f"无效的JWT: {e}")
            return JSONResponse(status_code=401, content={
                "code": -401,
                "message": "无效的身份验证令牌",
                "data": None,
            })
        
        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header[7:]
        token = request.headers.get("x-access-token")
        if token:
            return token
        return None

