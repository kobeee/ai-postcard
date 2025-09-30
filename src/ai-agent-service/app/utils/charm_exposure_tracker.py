"""
签体曝光追踪器
用于记录签体推荐历史和全局曝光统计
"""

import logging

logger = logging.getLogger(__name__)

class CharmExposureTracker:
    """签体曝光追踪器"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.global_key = "charm:exposure:global"

    def record_recommendation(self, user_id: str, charm_ids: list):
        """记录推荐结果"""
        try:
            pipeline = self.redis.pipeline()

            # 更新全局计数
            for charm_id in charm_ids:
                pipeline.hincrby(self.global_key, charm_id, 1)

            # 更新用户历史
            history_key = f"charm:history:{user_id}"
            for charm_id in charm_ids:
                pipeline.lpush(history_key, charm_id)
            pipeline.ltrim(history_key, 0, 4)  # 只保留5个
            pipeline.expire(history_key, 30 * 86400)

            pipeline.execute()
        except Exception as e:
            logger.error(f"❌ 记录推荐失败: {e}")

    def get_global_stats(self) -> dict:
        """获取全局统计"""
        try:
            stats = self.redis.hgetall(self.global_key)
            return {k.decode(): int(v) for k, v in stats.items()}
        except Exception as e:
            logger.error(f"❌ 获取统计失败: {e}")
            return {}

    def get_user_recent(self, user_id: str, limit: int = 5) -> list:
        """获取用户历史"""
        try:
            history_key = f"charm:history:{user_id}"
            recent = self.redis.lrange(history_key, 0, limit - 1)
            return [item.decode() for item in recent]
        except Exception as e:
            logger.error(f"❌ 获取历史失败: {e}")
            return []