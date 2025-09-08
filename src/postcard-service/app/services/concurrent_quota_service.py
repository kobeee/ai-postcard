# -*- coding: utf-8 -*-
"""
并发安全的配额服务
实现分布式锁和乐观锁的双重保护
"""

import uuid
import logging
import os
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from zoneinfo import ZoneInfo

from ..models.user_quota import UserQuota
from .distributed_lock_service import DistributedLockService, QuotaLockError, ConcurrentUpdateError

logger = logging.getLogger(__name__)


class ConcurrentSafeQuotaService:
    """并发安全的配额服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.lock_service = DistributedLockService()
        
        # 配置选项
        self.use_locks = os.getenv('QUOTA_LOCKS_ENABLED', 'false').lower() == 'true'
        self.legacy_quota_mode = os.getenv('LEGACY_QUOTA_MODE', 'true').lower() == 'true'
        self.timezone = os.getenv("APP_TIMEZONE", "Asia/Shanghai")
        
        # 并发控制参数
        self.max_retry = 3
        self.retry_delay = 0.1  # 100ms
        
        logger.info(f"⚡ 并发安全配额服务初始化: use_locks={self.use_locks}, legacy_mode={self.legacy_quota_mode}")

    def _today(self) -> date:
        """返回配置时区下的今天日期"""
        try:
            return datetime.now(ZoneInfo(self.timezone)).date()
        except Exception:
            return date.today()
    
    async def check_generation_quota(self, user_id: str) -> Dict[str, Any]:
        """检查用户是否可以生成新的明信片（线程安全版本）"""
        if not self.use_locks:
            # 回退到传统模式
            return await self._legacy_check_quota(user_id)
        
        try:
            # 🔥 使用分布式锁保护配额查询
            async with self.lock_service.quota_lock_context(user_id, "READ"):
                today = self._today()
                quota = self._get_user_quota_with_lock(user_id, today)
                
                return {
                    "can_generate": quota.can_generate,
                    "should_show_canvas": quota.should_show_canvas,
                    "remaining_quota": quota.remaining_quota,
                    "generated_count": quota.generated_count,
                    "current_card_exists": quota.current_card_exists,
                    "current_card_id": quota.current_card_id,
                    "max_daily_quota": quota.max_daily_quota,
                    "quota_date": quota.quota_date.isoformat(),
                    "version": getattr(quota, 'version', 1),  # 乐观锁版本
                    "message": self._get_quota_message(quota)
                }
                
        except Exception as e:
            logger.error(f"❌ 检查生成配额失败: {user_id} - {str(e)}")
            # 发生异常时回退到传统模式
            return await self._legacy_check_quota(user_id)
    
    async def consume_generation_quota_safe(self, user_id: str, card_id: str) -> bool:
        """并发安全的配额消费"""
        if not self.use_locks:
            # 回退到传统模式
            return await self._legacy_consume_quota(user_id, card_id)
        
        # 🔥 使用分布式锁保护
        try:
            async with self.lock_service.quota_lock_context(user_id, "CREATE"):
                return await self._consume_quota_with_optimistic_lock(user_id, card_id)
        except Exception as e:
            logger.error(f"❌ 并发安全配额消费失败: {user_id} - {str(e)}")
            if "无法获取分布式锁" in str(e):
                raise QuotaLockError("系统繁忙，请稍后重试")
            raise
    
    async def _consume_quota_with_optimistic_lock(self, user_id: str, card_id: str) -> bool:
        """使用乐观锁的配额消费"""
        for attempt in range(self.max_retry):
            try:
                # 🔥 使用SELECT FOR UPDATE防止读取时的竞态条件
                quota = self._get_user_quota_with_lock(user_id)
                
                # 严格检查配额
                if not quota.can_generate:
                    logger.warning(f"⚠️ 用户无法生成: {user_id} - 生成次数:{quota.generated_count}, 当前有卡片:{quota.current_card_exists}")
                    return False
                
                # 🔥 使用乐观锁更新配额
                old_version = getattr(quota, 'version', 1)
                new_version = old_version + 1
                
                # 构建乐观锁更新查询
                update_result = self.db.execute(
                    text("""
                    UPDATE user_quotas 
                    SET generated_count = :generated_count,
                        current_card_exists = :current_card_exists,
                        current_card_id = :current_card_id,
                        version = :new_version,
                        updated_at = :updated_at
                    WHERE user_id = :user_id 
                      AND quota_date = :quota_date 
                      AND version = :old_version
                    """),
                    {
                        "generated_count": quota.generated_count + 1,
                        "current_card_exists": True,
                        "current_card_id": card_id,
                        "new_version": new_version,
                        "updated_at": datetime.utcnow(),
                        "user_id": user_id,
                        "quota_date": quota.quota_date,
                        "old_version": old_version
                    }
                )
                
                if update_result.rowcount == 0:
                    # 版本冲突，重试
                    logger.warning(f"⚠️ 配额更新版本冲突，重试 {attempt + 1}/{self.max_retry}: {user_id}")
                    if attempt < self.max_retry - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise ConcurrentUpdateError("配额状态已被其他操作更新，请重试")
                
                self.db.commit()
                logger.info(f"✅ 安全消费配额: {user_id} - 卡片:{card_id} - 版本:{old_version}→{new_version}")
                return True
                    
            except SQLAlchemyError as e:
                try:
                    self.db.rollback()
                except:
                    pass
                logger.error(f"❌ 配额消费数据库错误: {user_id} - {str(e)}")
                if attempt == self.max_retry - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        raise ConcurrentUpdateError("配额消费失败，已重试多次")
    
    async def release_card_position_safe(self, user_id: str, card_id: str = None) -> bool:
        """并发安全的卡片位置释放"""
        if not self.use_locks:
            return await self._legacy_release_position(user_id, card_id)
        
        try:
            async with self.lock_service.quota_lock_context(user_id, "DELETE"):
                return await self._release_position_with_optimistic_lock(user_id, card_id)
        except Exception as e:
            logger.error(f"❌ 并发安全释放位置失败: {user_id} - {str(e)}")
            raise
    
    async def _release_position_with_optimistic_lock(self, user_id: str, card_id: str = None) -> bool:
        """使用乐观锁的位置释放"""
        for attempt in range(self.max_retry):
            try:
                quota = self._get_user_quota_with_lock(user_id)
                
                old_version = getattr(quota, 'version', 1)
                new_version = old_version + 1
                
                update_result = self.db.execute(
                    text("""
                    UPDATE user_quotas 
                    SET current_card_exists = :current_card_exists,
                        current_card_id = :current_card_id,
                        version = :new_version,
                        updated_at = :updated_at
                    WHERE user_id = :user_id 
                      AND quota_date = :quota_date 
                      AND version = :old_version
                    """),
                    {
                        "current_card_exists": False,
                        "current_card_id": None,
                        "new_version": new_version,
                        "updated_at": datetime.utcnow(),
                        "user_id": user_id,
                        "quota_date": quota.quota_date,
                        "old_version": old_version
                    }
                )
                
                if update_result.rowcount == 0:
                    logger.warning(f"⚠️ 释放位置版本冲突，重试 {attempt + 1}/{self.max_retry}: {user_id}")
                    if attempt < self.max_retry - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise ConcurrentUpdateError("配额状态已被其他操作更新，请重试")
                
                self.db.commit()
                logger.info(f"✅ 安全释放位置: {user_id} - 卡片:{card_id} - 版本:{old_version}→{new_version}")
                return True
                    
            except SQLAlchemyError as e:
                try:
                    self.db.rollback()
                except:
                    pass
                logger.error(f"❌ 释放位置数据库错误: {user_id} - {str(e)}")
                if attempt == self.max_retry - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        raise ConcurrentUpdateError("释放位置失败，已重试多次")
    
    async def handle_task_failure_safe(self, user_id: str, card_id: str) -> bool:
        """并发安全的任务失败处理"""
        if not self.use_locks:
            return await self._legacy_handle_failure(user_id, card_id)
        
        try:
            async with self.lock_service.quota_lock_context(user_id, "RECOVER"):
                return await self._handle_failure_with_optimistic_lock(user_id, card_id)
        except Exception as e:
            logger.error(f"❌ 并发安全任务失败处理失败: {user_id} - {str(e)}")
            raise
    
    async def _handle_failure_with_optimistic_lock(self, user_id: str, card_id: str) -> bool:
        """使用乐观锁的任务失败处理"""
        for attempt in range(self.max_retry):
            try:
                quota = self._get_user_quota_with_lock(user_id)
                
                if quota.current_card_id != card_id:
                    logger.warning(f"⚠️ 卡片ID不匹配: {user_id} - 期望:{card_id}, 实际:{quota.current_card_id}")
                    return False
                
                old_version = getattr(quota, 'version', 1)
                new_version = old_version + 1
                new_generated_count = max(0, quota.generated_count - 1)
                
                update_result = self.db.execute(
                    text("""
                    UPDATE user_quotas 
                    SET generated_count = :generated_count,
                        current_card_exists = :current_card_exists,
                        current_card_id = :current_card_id,
                        version = :new_version,
                        updated_at = :updated_at
                    WHERE user_id = :user_id 
                      AND quota_date = :quota_date 
                      AND version = :old_version
                    """),
                    {
                        "generated_count": new_generated_count,
                        "current_card_exists": False,
                        "current_card_id": None,
                        "new_version": new_version,
                        "updated_at": datetime.utcnow(),
                        "user_id": user_id,
                        "quota_date": quota.quota_date,
                        "old_version": old_version
                    }
                )
                
                if update_result.rowcount == 0:
                    logger.warning(f"⚠️ 任务失败处理版本冲突，重试 {attempt + 1}/{self.max_retry}: {user_id}")
                    if attempt < self.max_retry - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise ConcurrentUpdateError("配额状态已被其他操作更新，请重试")
                
                self.db.commit()
                logger.info(f"✅ 安全处理任务失败: {user_id} - 卡片:{card_id} - 恢复生成次数: {quota.generated_count}→{new_generated_count}")
                return True
                    
            except SQLAlchemyError as e:
                try:
                    self.db.rollback()
                except:
                    pass
                logger.error(f"❌ 任务失败处理数据库错误: {user_id} - {str(e)}")
                if attempt == self.max_retry - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        raise ConcurrentUpdateError("任务失败处理失败，已重试多次")
    
    def _get_user_quota_with_lock(self, user_id: str, quota_date: date = None) -> UserQuota:
        """使用悲观锁获取用户配额"""
        if quota_date is None:
            quota_date = self._today()
        
        # 🔥 使用SELECT FOR UPDATE悲观锁
        quota = self.db.query(UserQuota).filter(
            UserQuota.user_id == user_id,
            UserQuota.quota_date == quota_date
        ).with_for_update().first()
        
        if not quota:
            # 创建新配额记录
            quota = UserQuota(
                id=str(uuid.uuid4()),
                user_id=user_id,
                quota_date=quota_date,
                generated_count=0,
                current_card_exists=False,
                current_card_id=None,
                max_daily_quota=2,
                version=1  # 初始版本
            )
            self.db.add(quota)
            self.db.flush()  # 获取ID但不提交事务
        
        return quota
    
    # 传统模式方法（兼容性）
    async def _legacy_check_quota(self, user_id: str) -> Dict[str, Any]:
        """传统配额检查模式"""
        try:
            today = self._today()
            quota = self._get_user_quota_legacy(user_id, today)
            
            return {
                "can_generate": quota.can_generate,
                "should_show_canvas": quota.should_show_canvas,
                "remaining_quota": quota.remaining_quota,
                "generated_count": quota.generated_count,
                "current_card_exists": quota.current_card_exists,
                "current_card_id": quota.current_card_id,
                "max_daily_quota": quota.max_daily_quota,
                "quota_date": quota.quota_date.isoformat(),
                "message": self._get_quota_message(quota),
                "mode": "legacy"
            }
        except Exception as e:
            logger.error(f"❌ 传统配额检查失败: {user_id} - {str(e)}")
            raise
    
    def _get_user_quota_legacy(self, user_id: str, quota_date: date = None) -> UserQuota:
        """传统方式获取用户配额"""
        if quota_date is None:
            quota_date = self._today()
        
        quota = self.db.query(UserQuota).filter(
            UserQuota.user_id == user_id,
            UserQuota.quota_date == quota_date
        ).first()
        
        if not quota:
            quota = UserQuota(
                id=str(uuid.uuid4()),
                user_id=user_id,
                quota_date=quota_date,
                generated_count=0,
                current_card_exists=False,
                current_card_id=None,
                max_daily_quota=2
            )
            self.db.add(quota)
            self.db.commit()
            self.db.refresh(quota)
        
        return quota
    
    async def _legacy_consume_quota(self, user_id: str, card_id: str) -> bool:
        """传统配额消费模式"""
        try:
            quota = self._get_user_quota_legacy(user_id)
            
            if not quota.can_generate:
                logger.warning(f"⚠️ 用户无法生成: {user_id}")
                return False
            
            quota.generated_count += 1
            quota.current_card_exists = True
            quota.current_card_id = card_id
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"✅ 传统消费配额: {user_id} - 卡片:{card_id}")
            return True
            
        except SQLAlchemyError as e:
            try:
                self.db.rollback()
            except:
                pass
            logger.error(f"❌ 传统配额消费失败: {user_id} - {str(e)}")
            raise
    
    async def _legacy_release_position(self, user_id: str, card_id: str = None) -> bool:
        """传统位置释放模式"""
        try:
            quota = self._get_user_quota_legacy(user_id)
            
            quota.current_card_exists = False
            quota.current_card_id = None
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"✅ 传统释放位置: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            try:
                self.db.rollback()
            except:
                pass
            logger.error(f"❌ 传统释放位置失败: {user_id} - {str(e)}")
            raise
    
    async def _legacy_handle_failure(self, user_id: str, card_id: str) -> bool:
        """传统任务失败处理模式"""
        try:
            quota = self._get_user_quota_legacy(user_id)
            
            if quota.current_card_id == card_id:
                quota.current_card_exists = False
                quota.current_card_id = None
                if quota.generated_count > 0:
                    quota.generated_count -= 1
                quota.updated_at = datetime.utcnow()
                
                self.db.commit()
                logger.info(f"✅ 传统处理任务失败: {user_id}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            try:
                self.db.rollback()
            except:
                pass
            logger.error(f"❌ 传统任务失败处理失败: {user_id} - {str(e)}")
            raise
    
    def _get_quota_message(self, quota: UserQuota) -> str:
        """生成配额提示消息"""
        if quota.current_card_exists:
            return "今日已有生成的卡片，请先删除再生成新卡片"
        elif quota.can_generate:
            return f"今日还可生成 {quota.remaining_quota} 张明信片（已生成 {quota.generated_count} 张）"
        else:
            return f"今日生成次数已用完（已生成 {quota.generated_count} 张）。明天可重新生成 {quota.max_daily_quota} 张。"