from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging
from typing import Optional, Dict, Any

from ..models.user import User

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def find_user_by_openid(self, openid: str) -> Optional[User]:
        """根据OpenID查找用户"""
        try:
            user = self.db.query(User).filter(User.openid == openid).first()
            return user
        except Exception as e:
            logger.error(f"查找用户失败: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            raise
    
    async def create_miniprogram_user(self, user_data: Dict[str, Any]) -> User:
        """创建小程序用户"""
        try:
            user = User(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"创建用户成功: {user.id}")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"用户创建失败，可能已存在: {e}")
            raise ValueError("用户已存在")
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建用户失败: {e}")
            raise
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> User:
        """更新用户信息"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"更新用户成功: {user.id}")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新用户失败: {e}")
            raise
    
    async def update_last_login(self, user_id: str) -> bool:
        """更新最后登录时间"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新登录时间失败: {e}")
            return False
    
    async def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                user.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"用户已停用: {user_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"停用用户失败: {e}")
            return False
    
    async def get_user_stats(self) -> Dict[str, int]:
        """获取用户统计信息"""
        try:
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter(User.is_active == True).count()
            premium_users = self.db.query(User).filter(User.is_premium == True).count()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "premium_users": premium_users
            }
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "premium_users": 0
            }