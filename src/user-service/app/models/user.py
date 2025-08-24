from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
try:
    from ..database.connection import Base
except ImportError:
    from app.database.connection import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 微信相关信息
    openid = Column(String(100), unique=True, nullable=False, comment="微信OpenID")
    unionid = Column(String(100), unique=True, nullable=True, comment="微信UnionID")
    session_key = Column(String(100), nullable=True, comment="微信会话密钥")
    
    # 用户基本信息
    nickname = Column(String(50), nullable=False, default="微信用户", comment="用户昵称")
    avatar_url = Column(Text, nullable=True, comment="头像URL")
    gender = Column(Integer, default=0, comment="性别：0-未知，1-男，2-女")
    
    # 地理信息
    country = Column(String(50), nullable=True, comment="国家")
    province = Column(String(50), nullable=True, comment="省份")
    city = Column(String(50), nullable=True, comment="城市")
    language = Column(String(10), default="zh_CN", comment="语言")
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_premium = Column(Boolean, default=False, comment="是否为高级用户")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "openid": self.openid,
            "unionid": self.unionid,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "gender": self.gender,
            "country": self.country,
            "province": self.province,
            "city": self.city,
            "language": self.language,
            "is_active": self.is_active,
            "is_premium": self.is_premium,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    def __repr__(self):
        return f"<User(id={self.id}, nickname={self.nickname}, openid={self.openid})>"