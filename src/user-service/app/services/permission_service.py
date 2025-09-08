# -*- coding: utf-8 -*-
"""
权限管理服务
实现RBAC权限控制和资源所有权管理
"""

import os
import logging
import functools
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, Depends

from ..database.connection import get_db
from ..services.auth_service import CurrentUser
from ..middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)


class PermissionError(Exception):
    """权限验证异常"""
    pass


class ResourceOwnershipService:
    """资源所有权管理服务"""
    
    def __init__(self, db: Session = None):
        self.db = db
        # 权限级别配置
        self.permission_level = os.getenv('PERMISSION_LEVEL', 'none')
        # none: 无权限检查
        # basic: 基础资源所有权检查  
        # full: 完整RBAC权限检查
        
        logger.debug(f"🛡️ 权限服务初始化: permission_level={self.permission_level}")
    
    async def register_ownership(self, resource_type: str, resource_id: str, owner_id: str) -> bool:
        """注册资源所有权"""
        try:
            if self.permission_level == 'none':
                return True  # 不检查权限时，总是返回成功
            
            # 在实际项目中，这里会插入到resource_ownership表
            # 现在使用Redis作为临时存储
            from ..services.auth_service import AuthService
            auth_service = AuthService()
            
            ownership_key = f"resource_ownership:{resource_type}:{resource_id}"
            ownership_data = {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "owner_id": owner_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await auth_service.redis.setex(
                ownership_key, 
                30 * 24 * 3600,  # 30天过期
                str(ownership_data)
            )
            
            logger.info(f"✅ 注册资源所有权: {resource_type}:{resource_id} -> {owner_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 注册资源所有权失败: {str(e)}")
            return False
    
    async def check_ownership(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        """检查资源所有权"""
        try:
            if self.permission_level == 'none':
                return True  # 不检查权限时，总是返回通过
            
            # 从Redis查询所有权
            from ..services.auth_service import AuthService
            auth_service = AuthService()
            
            ownership_key = f"resource_ownership:{resource_type}:{resource_id}"
            ownership_data = await auth_service.redis.get(ownership_key)
            
            if ownership_data:
                # 解析所有权数据
                try:
                    import ast
                    ownership_dict = ast.literal_eval(ownership_data.decode())
                    owner_id = ownership_dict.get("owner_id")
                    
                    result = owner_id == user_id
                    logger.debug(f"🔍 资源所有权检查: {resource_type}:{resource_id} owner={owner_id} user={user_id} result={result}")
                    return result
                except Exception as parse_error:
                    logger.warning(f"解析所有权数据失败: {str(parse_error)}")
                    return False
            else:
                # 资源未注册所有权，尝试从资源本身推断
                return await self._infer_ownership_from_resource(resource_type, resource_id, user_id)
                
        except Exception as e:
            logger.error(f"❌ 检查资源所有权失败: {str(e)}")
            return False
    
    async def _infer_ownership_from_resource(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        """从资源本身推断所有权"""
        try:
            if resource_type == "postcard":
                # 查询明信片的所有者
                from ..models.user import User  # 假设有这个模型
                
                # 这里应该查询postcard表，暂时使用简化逻辑
                logger.warning(f"⚠️ 无法查询明信片所有权，允许访问: {resource_id}")
                return True  # 临时允许，实际部署时需要实现数据库查询
                
            elif resource_type == "quota":
                # 配额资源通常按用户ID匹配
                return resource_id == user_id
                
            return False
            
        except Exception as e:
            logger.error(f"推断资源所有权失败: {str(e)}")
            return False
    
    async def transfer_ownership(self, resource_type: str, resource_id: str, new_owner_id: str) -> bool:
        """转移资源所有权"""
        try:
            from ..services.auth_service import AuthService
            auth_service = AuthService()
            
            ownership_key = f"resource_ownership:{resource_type}:{resource_id}"
            ownership_data = {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "owner_id": new_owner_id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await auth_service.redis.setex(ownership_key, 30 * 24 * 3600, str(ownership_data))
            
            logger.info(f"✅ 转移资源所有权: {resource_type}:{resource_id} -> {new_owner_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 转移资源所有权失败: {str(e)}")
            return False


class ProgressivePermissionControl:
    """渐进式权限控制"""
    
    def __init__(self):
        self.permission_level = os.getenv('PERMISSION_LEVEL', 'none')
        logger.info(f"🛡️ 权限控制级别: {self.permission_level}")
    
    async def check_permission(self, user: CurrentUser, resource_type: str, action: str, resource_id: str = None) -> bool:
        """检查用户权限"""
        try:
            if self.permission_level == 'none':
                logger.debug("🔓 权限级别为none，跳过权限检查")
                return True  # 完全兼容当前无权限状态
                
            elif self.permission_level == 'basic':
                # 只检查资源所有权
                if resource_id:
                    ownership_service = ResourceOwnershipService()
                    result = await ownership_service.check_ownership(resource_type, resource_id, user.user_id)
                    logger.debug(f"🔍 基础权限检查 (所有权): {result}")
                    return result
                else:
                    # 没有资源ID，检查基础权限
                    permission = f"{resource_type}:{action}"
                    result = user.has_permission(permission)
                    logger.debug(f"🔍 基础权限检查 (权限): {permission} -> {result}")
                    return result
                    
            elif self.permission_level == 'full':
                # 完整权限检查
                permission = f"{resource_type}:{action}"
                has_permission = user.has_permission(permission)
                
                # 如果有资源ID，还需要检查所有权
                if resource_id and has_permission:
                    ownership_service = ResourceOwnershipService()
                    has_ownership = await ownership_service.check_ownership(resource_type, resource_id, user.user_id)
                    result = has_permission and has_ownership
                    logger.debug(f"🔍 完整权限检查: permission={has_permission}, ownership={has_ownership}, result={result}")
                    return result
                else:
                    logger.debug(f"🔍 完整权限检查 (仅权限): {permission} -> {has_permission}")
                    return has_permission
                    
            return False
            
        except Exception as e:
            logger.error(f"❌ 权限检查异常: {str(e)}")
            return False


# 权限验证装饰器
def require_permission(permission: str, resource_check: bool = False):
    """
    权限验证装饰器
    
    Args:
        permission: 需要的权限，如 "postcard:create", "postcard:delete"
        resource_check: 是否需要检查资源所有权
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户（由身份验证中间件注入）
            request = None
            current_user = None
            
            # 从参数中查找Request和CurrentUser对象
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # 从依赖注入中获取当前用户
            for key, value in kwargs.items():
                if isinstance(value, CurrentUser):
                    current_user = value
                    break
            
            # 如果没有找到用户，尝试从request.state获取
            if not current_user and request and hasattr(request.state, 'user'):
                current_user = request.state.user
            
            if not current_user:
                raise PermissionError("用户身份验证失败")
            
            # 解析权限
            resource_type, action = permission.split(':') if ':' in permission else (permission, 'access')
            
            # 获取资源ID（如果需要）
            resource_id = None
            if resource_check:
                resource_id = (kwargs.get('postcard_id') or 
                             kwargs.get('resource_id') or 
                             kwargs.get('id') or
                             kwargs.get('user_id'))
                
                if not resource_id:
                    raise PermissionError("缺少资源标识")
            
            # 执行权限检查
            permission_control = ProgressivePermissionControl()
            has_permission = await permission_control.check_permission(
                current_user, resource_type, action, resource_id
            )
            
            if not has_permission:
                raise PermissionError(f"权限不足: 需要 {permission}")
            
            # 权限检查通过，执行原函数
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


# 资源所有权注册装饰器
def register_resource_ownership(resource_type: str, resource_id_param: str = "id", owner_id_param: str = "user_id"):
    """
    资源所有权注册装饰器
    
    Args:
        resource_type: 资源类型，如 "postcard"
        resource_id_param: 资源ID参数名
        owner_id_param: 所有者ID参数名
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行原函数
            result = await func(*args, **kwargs)
            
            try:
                # 获取资源ID和所有者ID
                resource_id = kwargs.get(resource_id_param)
                owner_id = kwargs.get(owner_id_param)
                
                # 如果是创建操作，从结果中获取ID
                if not resource_id and isinstance(result, dict):
                    if "data" in result and isinstance(result["data"], dict):
                        resource_id = result["data"].get("id") or result["data"].get("task_id")
                
                # 从当前用户获取所有者ID
                if not owner_id:
                    for arg in args:
                        if isinstance(arg, Request) and hasattr(arg.state, 'user'):
                            owner_id = arg.state.user.user_id
                            break
                    
                    for key, value in kwargs.items():
                        if isinstance(value, CurrentUser):
                            owner_id = value.user_id
                            break
                
                # 注册所有权
                if resource_id and owner_id:
                    ownership_service = ResourceOwnershipService()
                    await ownership_service.register_ownership(resource_type, resource_id, owner_id)
                    logger.debug(f"📝 已注册资源所有权: {resource_type}:{resource_id} -> {owner_id}")
            
            except Exception as e:
                logger.warning(f"⚠️ 注册资源所有权失败: {str(e)}")
                # 不影响主流程，只记录警告
            
            return result
            
        return wrapper
    return decorator


# FastAPI依赖注入函数
async def require_admin_permission(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


async def require_premium_permission(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """要求高级用户权限"""
    if current_user.role not in ["premium_user", "admin"]:
        raise HTTPException(status_code=403, detail="需要高级用户权限")
    return current_user


async def check_resource_ownership(
    resource_type: str,
    resource_id: str, 
    current_user: CurrentUser = Depends(get_current_user)
) -> bool:
    """检查资源所有权（依赖注入版本）"""
    ownership_service = ResourceOwnershipService()
    has_ownership = await ownership_service.check_ownership(resource_type, resource_id, current_user.user_id)
    
    if not has_ownership:
        raise HTTPException(status_code=403, detail="您无权访问该资源")
    
    return True