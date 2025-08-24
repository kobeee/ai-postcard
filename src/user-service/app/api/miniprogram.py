from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging
import requests
from jose import jwt
from datetime import datetime, timedelta

from ..database.connection import get_db
from ..models.user import User
from ..services.user_service import UserService
from pydantic import BaseModel

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/miniprogram")

# 微信小程序配置（从环境变量获取）
import os
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "wx1234567890abcdef")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "your_app_secret_here")
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_here")

class WechatLoginRequest(BaseModel):
    code: str  # 微信登录临时代码
    userInfo: dict  # 用户信息（头像、昵称等）

class RefreshTokenRequest(BaseModel):
    refreshToken: str

@router.post("/auth/login")
async def miniprogram_login(
    request: WechatLoginRequest,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：微信登录"""
    try:
        logger.info(f"小程序用户登录请求: {request.code[:10]}...")
        
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
                "session_key": session_key
            }
            
            user = await service.create_miniprogram_user(user_data)
            logger.info(f"创建新小程序用户: {user.id}")
        else:
            # 更新现有用户信息
            update_data = {
                "nickname": request.userInfo.get("nickName", user.nickname),
                "avatar_url": request.userInfo.get("avatarUrl", user.avatar_url),
                "session_key": session_key,
                "last_login_at": datetime.now()
            }
            
            user = await service.update_user(user.id, update_data)
            logger.info(f"更新小程序用户: {user.id}")
        
        # 3. 生成JWT令牌
        access_token = generate_jwt_token(str(user.id), "access", expires_hours=24)
        refresh_token = generate_jwt_token(str(user.id), "refresh", expires_hours=24*30)  # 30天
        
        return {
            "code": 0,
            "message": "登录成功",
            "data": {
                "token": access_token,
                "refreshToken": refresh_token,
                "userInfo": {
                    "id": str(user.id),
                    "openid": user.openid,
                    "nickname": user.nickname,
                    "avatar_url": user.avatar_url,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }
        }
    except Exception as e:
        logger.error(f"小程序登录失败: {str(e)}")
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
    """小程序：刷新访问令牌"""
    try:
        # 验证refresh token
        payload = jwt.decode(request.refreshToken, JWT_SECRET, algorithms=["HS256"])
        
        if payload.get("type") != "refresh":
            return {
                "code": -1,
                "message": "无效的刷新令牌",
                "data": None
            }
        
        user_id = payload.get("user_id")
        
        # 获取用户信息
        service = UserService(db)
        user = await service.get_user_by_id(user_id)
        
        if not user:
            return {
                "code": -1,
                "message": "用户不存在",
                "data": None
            }
        
        # 生成新的访问令牌
        access_token = generate_jwt_token(str(user.id), "access", expires_hours=24)
        
        return {
            "code": 0,
            "message": "令牌刷新成功",
            "data": {
                "token": access_token,
                "userInfo": {
                    "id": str(user.id),
                    "openid": user.openid,
                    "nickname": user.nickname,
                    "avatar_url": user.avatar_url
                }
            }
        }
    except jwt.ExpiredSignatureError:
        return {
            "code": -1,
            "message": "刷新令牌已过期",
            "data": None
        }
    except jwt.JWTError:
        return {
            "code": -1,
            "message": "无效的刷新令牌",
            "data": None
        }
    except Exception as e:
        logger.error(f"刷新令牌失败: {str(e)}")
        return {
            "code": -1,
            "message": f"刷新失败: {str(e)}",
            "data": None
        }

@router.get("/auth/userinfo")
async def get_miniprogram_user_info(
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """小程序：获取用户信息"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return {
                "code": -1,
                "message": "缺少认证令牌",
                "data": None
            }
        
        token = authorization.split(" ")[1]
        
        # 验证JWT令牌
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if payload.get("type") != "access":
            return {
                "code": -1,
                "message": "无效的访问令牌",
                "data": None
            }
        
        # 获取用户信息
        service = UserService(db)
        user = await service.get_user_by_id(user_id)
        
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
                "gender": user.gender,
                "country": user.country,
                "province": user.province,
                "city": user.city,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            }
        }
    except jwt.ExpiredSignatureError:
        return {
            "code": -1,
            "message": "访问令牌已过期",
            "data": None
        }
    except jwt.JWTError:
        return {
            "code": -1,
            "message": "无效的访问令牌",
            "data": None
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取用户信息失败: {str(e)}",
            "data": None
        }

async def exchange_wechat_code(code: str) -> dict:
    """使用微信code换取session_key和openid"""
    # 开发环境检测：使用测试AppID时，所有code都走模拟模式
    is_test_env = WECHAT_APP_ID in ["wx1d61d190473ed728", "wx1234567890abcdef"] or WECHAT_APP_SECRET in ["test_secret_for_development", "your_app_secret_here"]
    
    # 测试环境下，如果code以test_开头，或者使用测试AppID，返回模拟数据
    if code.startswith("test_") or is_test_env:
        logger.info(f"使用测试模式处理微信登录，code: {code[:10]}...")
        return {
            "openid": f"test_openid_{code[-6:] if len(code) > 6 else code}",
            "session_key": f"test_session_{code[-6:] if len(code) > 6 else code}",
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

def generate_jwt_token(user_id: str, token_type: str = "access", expires_hours: int = 24) -> str:
    """生成JWT令牌"""
    payload = {
        "user_id": user_id,
        "type": token_type,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")