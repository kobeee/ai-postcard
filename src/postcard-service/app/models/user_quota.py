from sqlalchemy import Column, String, Integer, DateTime, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, date

Base = declarative_base()

class UserQuota(Base):
    """用户每日生成配额模型 - 每天最多生成2次，删除不恢复配额"""
    __tablename__ = "user_quotas"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # 用户ID
    quota_date = Column(Date, nullable=False, index=True)  # 配额日期
    generated_count = Column(Integer, default=0)  # 今日总生成次数（只增不减）
    current_card_exists = Column(Boolean, default=False)  # 当前是否有今日卡片
    current_card_id = Column(String, nullable=True)  # 当前卡片ID（可选引用）
    max_daily_quota = Column(Integer, default=2)  # 每日最大生成次数
    version = Column(Integer, default=1)  # 乐观锁版本号
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserQuota(user_id={self.user_id}, date={self.quota_date}, generated={self.generated_count}/{self.max_daily_quota}, has_card={self.current_card_exists})>"
    
    @property 
    def remaining_quota(self):
        """剩余生成次数 = 最大配额 - 已生成次数"""
        return max(0, self.max_daily_quota - self.generated_count)
    
    @property
    def can_generate(self):
        """是否可以生成：有剩余配额 且 当前无卡片"""
        return self.remaining_quota > 0 and not self.current_card_exists
    
    @property
    def should_show_canvas(self):
        """是否显示画布：当前没有卡片时显示"""
        return not self.current_card_exists