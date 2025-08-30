import uuid
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.user_quota import UserQuota

logger = logging.getLogger(__name__)

class QuotaService:
    """用户配额服务 - 每天最多生成2次，删除不恢复配额，只释放今日卡片位置"""
    
    def __init__(self, db: Session):
        self.db = db

    async def get_user_quota(self, user_id: str, quota_date: date = None) -> UserQuota:
        """获取用户的配额信息，如果不存在则创建"""
        try:
            if quota_date is None:
                quota_date = date.today()
            
            # 查找现有配额记录
            quota = self.db.query(UserQuota).filter(
                UserQuota.user_id == user_id,
                UserQuota.quota_date == quota_date
            ).first()
            
            # 如果不存在，创建新记录
            if not quota:
                quota = UserQuota(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    quota_date=quota_date,
                    generated_count=0,
                    current_card_exists=False,
                    current_card_id=None,
                    max_daily_quota=2  # 默认每日2次
                )
                self.db.add(quota)
                self.db.commit()
                self.db.refresh(quota)
                logger.info(f"✅ 创建用户配额记录: {user_id} - {quota_date}")
            
            return quota
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 获取用户配额失败: {user_id} - {e}")
            raise

    async def check_generation_quota(self, user_id: str) -> Dict[str, Any]:
        """检查用户是否可以生成新的明信片"""
        try:
            today = date.today()
            quota = await self.get_user_quota(user_id, today)
            
            return {
                "can_generate": quota.can_generate,
                "should_show_canvas": quota.should_show_canvas,
                "remaining_quota": quota.remaining_quota,
                "generated_count": quota.generated_count,
                "current_card_exists": quota.current_card_exists,
                "current_card_id": quota.current_card_id,
                "max_daily_quota": quota.max_daily_quota,
                "quota_date": quota.quota_date.isoformat(),
                "message": self._get_quota_message(quota)
            }
            
        except Exception as e:
            logger.error(f"❌ 检查生成配额失败: {user_id} - {e}")
            raise

    async def consume_generation_quota(self, user_id: str, card_id: str) -> bool:
        """消耗生成配额（用户生成新明信片时调用）"""
        try:
            today = date.today()
            quota = await self.get_user_quota(user_id, today)
            
            if not quota.can_generate:
                logger.warning(f"⚠️ 用户无法生成: {user_id} - 生成次数:{quota.generated_count}, 当前有卡片:{quota.current_card_exists}")
                return False
            
            # 增加已生成数量，设置当前卡片
            quota.generated_count += 1
            quota.current_card_exists = True
            quota.current_card_id = card_id
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(quota)
            
            logger.info(f"✅ 消耗生成配额: {user_id} - 卡片ID:{card_id} - 剩余次数: {quota.remaining_quota}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 消耗生成配额失败: {user_id} - {e}")
            raise

    async def release_card_position(self, user_id: str, card_id: str = None) -> bool:
        """释放今日卡片位置（用户删除明信片时调用）- 不恢复生成次数"""
        try:
            today = date.today()
            quota = await self.get_user_quota(user_id, today)
            
            # 只释放位置，不恢复生成次数
            quota.current_card_exists = False
            quota.current_card_id = None
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(quota)
            
            logger.info(f"✅ 释放卡片位置: {user_id} - 卡片ID:{card_id} - 生成次数不变: {quota.generated_count}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 释放卡片位置失败: {user_id} - {e}")
            raise

    async def set_user_quota(self, user_id: str, max_daily_quota: int) -> bool:
        """设置用户的每日配额（管理员功能）"""
        try:
            today = date.today()
            quota = await self.get_user_quota(user_id, today)
            
            quota.max_daily_quota = max_daily_quota
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(quota)
            
            logger.info(f"✅ 设置用户配额: {user_id} - 每日: {max_daily_quota}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 设置用户配额失败: {user_id} - {e}")
            raise

    def _get_quota_message(self, quota: UserQuota) -> str:
        """生成配额提示消息"""
        if quota.current_card_exists:
            return "今日已有生成的卡片，请先删除再生成新卡片"
        elif quota.can_generate:
            return f"今日还可生成 {quota.remaining_quota} 张明信片（已生成 {quota.generated_count} 张）"
        else:
            return f"今日生成次数已用完（已生成 {quota.generated_count} 张）。明天可重新生成 {quota.max_daily_quota} 张。"