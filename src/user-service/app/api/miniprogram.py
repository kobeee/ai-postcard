from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging
import requests
from datetime import datetime, timedelta
import uuid

from ..database.connection import get_db
from ..models.user import User
from ..services.user_service import UserService
from ..services.auth_service import AuthService, CurrentUser
from ..middleware.auth_middleware import get_current_user, require_authentication
from pydantic import BaseModel

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/miniprogram")

# 微信小程序配置（从环境变量获取）
import os
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "wx1234567890abcdef")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "your_app_secret_here")

class WechatLoginRequest(BaseModel):
    code: str  # 微信登录临时代码
    userInfo: dict  # 用户信息（头像、昵称等）

class RefreshTokenRequest(BaseModel):
    refreshToken: str
    sessionId: Optional[str] = None

class LogoutRequest(BaseModel):
    sessionId: Optional[str] = None

@router.post("/auth/login")
async def miniprogram_login(
    request: WechatLoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全微信登录（JWT版本）"""
    auth_service = AuthService()
    
    try:
        logger.info(f"🔐 小程序安全登录请求: {request.code[:10]}...")
        
        # 1. 使用code换取session_key和openid
        wechat_response = await exchange_wechat_code(request.code)
        
        if "errcode" in wechat_response:
            return {
                "code": -1,
                "message": f"微信登录失败: {wechat_response.get('errmsg', '未知错误')}",
                "data": None
            }
        
        openid = wechat_response.get("openid")
        session_key = wechat_response.get("session_key")
        unionid = wechat_response.get("unionid")  # 可能为空
        
        if not openid:
            return {
                "code": -1,
                "message": "获取用户OpenID失败",
                "data": None
            }
        
        # 2. 查找或创建用户
        service = UserService(db)
        user = await service.find_user_by_openid(openid)
        
        if not user:
            # 创建新用户
            user_data = {
                "openid": openid,
                "unionid": unionid,
                "nickname": request.userInfo.get("nickName", "微信用户"),
                "avatar_url": request.userInfo.get("avatarUrl", ""),
                "gender": request.userInfo.get("gender", 0),
                "country": request.userInfo.get("country", ""),
                "province": request.userInfo.get("province", ""),
                "city": request.userInfo.get("city", ""),
                "language": request.userInfo.get("language", "zh_CN"),
                "session_key": session_key,
                "role": "user"  # 默认角色
            }
            
            user = await service.create_miniprogram_user(user_data)
            logger.info(f"✅ 创建新小程序用户: {user.id}")
        else:
            # 更新现有用户信息
            update_data = {
                "nickname": request.userInfo.get("nickName", user.nickname),
                "avatar_url": request.userInfo.get("avatarUrl", user.avatar_url),
                "session_key": session_key,
                "last_login_at": datetime.now()
            }
            
            user = await service.update_user(user.id, update_data)
            logger.info(f"✅ 更新小程序用户: {user.id}")
        
        # 3. 🔥 使用新的AuthService生成安全JWT令牌
        user_dict = {
            "id": str(user.id),
            "openid": user.openid,
            "role": getattr(user, 'role', 'user'),
            "nickname": user.nickname,
            "avatar": user.avatar_url
        }
        
        access_token = await auth_service.create_access_token(user_dict)
        refresh_token = await auth_service.create_refresh_token(str(user.id))
        
        # 4. 🔥 记录登录审计日志（简化版）
        client_ip = getattr(http_request.client, 'host', 'unknown')
        logger.info(f"🔐 安全登录成功: 用户 {user.id}, IP: {client_ip}")
        
        # 5. 解析访问Token以获取会话信息
        try:
            token_payload = await auth_service.verify_token(access_token)
            session_id = token_payload.get("session_id")
            jti = token_payload.get("jti")
        except Exception:
            session_id = None
            jti = None
        
        return {
            "code": 0,
            "message": "登录成功",
            "data": {
                "token": access_token,
                "refreshToken": refresh_token,
                "expiresIn": 7 * 24 * 3600,  # 7天
                "sessionId": session_id,
                "jti": jti,
                "userInfo": {
                    "id": str(user.id),
                    "openid": user.openid,
                    "nickname": user.nickname,
                    "avatar": user.avatar_url,
                    "role": getattr(user, 'role', 'user'),
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }
        }
    except Exception as e:
        logger.error(f"❌ 小程序安全登录失败: {str(e)}")
        return {
            "code": -1,
            "message": f"登录失败: {str(e)}",
            "data": None
        }

@router.post("/auth/refresh")
async def refresh_miniprogram_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全刷新访问令牌（JWT版本）"""
    auth_service = AuthService()
    
    try:
        logger.info(f"🔄 Token刷新请求: session_id={request.sessionId}")
        
        # 🔥 使用新的AuthService刷新Token
        refresh_result = await auth_service.refresh_access_token(
            request.refreshToken, 
            request.sessionId
        )
        
        # 解析新访问Token以获取会话信息
        try:
            token_payload = await auth_service.verify_token(refresh_result["access_token"])
            session_id = token_payload.get("session_id")
            jti = token_payload.get("jti")
        except Exception:
            session_id = None
            jti = None
        
        return {
            "code": 0,
            "message": "令牌刷新成功",
            "data": {
                "token": refresh_result["access_token"],
                "refreshToken": refresh_result["refresh_token"],
                "expiresIn": refresh_result["expires_in"],
                "sessionId": session_id,
                "jti": jti,
                "userInfo": refresh_result["user"]
            }
        }
    except HTTPException as e:
        if e.status_code == 401:
            return {
                "code": -401,
                "message": e.detail,
                "data": None
            }
        else:
            return {
                "code": -1,
                "message": f"令牌刷新失败: {e.detail}",
                "data": None
            }
    except Exception as e:
        logger.error(f"❌ 令牌刷新失败: {str(e)}")
        return {
            "code": -1,
            "message": f"刷新失败: {str(e)}",
            "data": None
        }

@router.get("/auth/userinfo")
async def get_miniprogram_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：获取用户信息（安全版本）"""
    try:
        logger.info(f"📋 获取用户信息: {current_user.user_id}")
        
        # 获取完整的用户信息
        service = UserService(db)
        user = await service.get_user_by_id(current_user.user_id)
        
        if not user:
            return {
                "code": -1,
                "message": "用户不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取用户信息成功",
            "data": {
                "id": str(user.id),
                "openid": user.openid,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
                "gender": getattr(user, 'gender', 0),
                "country": getattr(user, 'country', ''),
                "province": getattr(user, 'province', ''),
                "city": getattr(user, 'city', ''),
                "role": current_user.role,
                "permissions": list(current_user.permissions),
                "session_id": current_user.session_id,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": getattr(user, 'last_login_at', None).isoformat() if getattr(user, 'last_login_at', None) else None
            }
        }
    except Exception as e:
        logger.error(f"❌ 获取用户信息失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取用户信息失败: {str(e)}",
            "data": None
        }

@router.post("/auth/logout")
async def miniprogram_logout(
    request: LogoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    http_request: Request = None
):
    """🔥 小程序：安全登出（撤销Token）"""
    auth_service = AuthService()
    
    try:
        logger.info(f"🚪 用户登出: {current_user.user_id}, session: {request.sessionId}")
        
        # 撤销用户的所有Token
        await auth_service.revoke_user_tokens(current_user.user_id)
        
        # 记录登出审计日志（简化版）
        if http_request:
            client_ip = getattr(http_request.client, 'host', 'unknown')
            logger.info(f"🔐 安全登出成功: 用户 {current_user.user_id}, IP: {client_ip}")
        
        return {
            "code": 0,
            "message": "登出成功",
            "data": {
                "user_id": current_user.user_id,
                "logout_time": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"❌ 登出失败: {str(e)}")
        return {
            "code": -1,
            "message": f"登出失败: {str(e)}",
            "data": None
        }

async def exchange_wechat_code(code: str) -> dict:
    """使用微信code换取session_key和openid"""
    # 开发环境检测：使用测试AppID时，所有code都走模拟模式
    is_test_env = (
        not WECHAT_APP_ID or 
        not WECHAT_APP_SECRET or
        WECHAT_APP_ID in ["wx1d61d190473ed728", "wx1234567890abcdef"] or 
        WECHAT_APP_SECRET in ["test_secret_for_development", "your_app_secret_here"]
    )
    
    # 测试环境下，如果code以test_开头，或者使用测试AppID，返回模拟数据
    if code.startswith("test_") or is_test_env:
        logger.info(f"🧪 开发测试模式：微信登录模拟成功，code: {code[:10]}...")
        # 生成稳定的测试数据，方便开发调试
        import hashlib
        stable_id = hashlib.md5(code.encode()).hexdigest()[:8]
        return {
            "openid": f"dev_openid_{stable_id}",
            "session_key": f"dev_session_{stable_id}",
            "unionid": None
        }
    
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WECHAT_APP_ID,
        "secret": WECHAT_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"微信API请求失败: {str(e)}")
        return {"errcode": -1, "errmsg": "微信服务器连接失败"}

# 🔥 旧的JWT生成函数已被新的AuthService替代