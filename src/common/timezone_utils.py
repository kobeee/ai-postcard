"""
时区管理工具 - 统一使用 Asia/Shanghai 时区
确保整个系统时间的一致性和准确性
"""

import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# 强制使用中国时区 Asia/Shanghai
CHINA_TIMEZONE = ZoneInfo("Asia/Shanghai")

class TimezoneUtils:
    """统一时区管理工具类"""
    
    @staticmethod
    def now() -> datetime:
        """获取当前 Asia/Shanghai 时区的时间"""
        return datetime.now(CHINA_TIMEZONE)
    
    @staticmethod
    def utcnow() -> datetime:
        """获取当前UTC时间 (已弃用，建议使用 now())"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def to_china_time(dt: datetime) -> datetime:
        """将datetime转换为中国时区时间"""
        if dt.tzinfo is None:
            # 如果没有时区信息，假设为UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CHINA_TIMEZONE)
    
    @staticmethod
    def get_china_date():
        """获取当前中国时区的日期"""
        return TimezoneUtils.now().date()
    
    @staticmethod
    def format_china_time(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化中国时区时间"""
        if dt is None:
            dt = TimezoneUtils.now()
        else:
            dt = TimezoneUtils.to_china_time(dt)
        return dt.strftime(format_str)

# 兼容性函数 - 替代 datetime.now() 和 datetime.utcnow()
def china_now() -> datetime:
    """替代 datetime.now() - 返回中国时区时间"""
    return TimezoneUtils.now()

def china_utcnow() -> datetime:
    """替代 datetime.utcnow() - 但返回中国时区时间"""
    return TimezoneUtils.now()

def china_date():
    """获取中国时区的当前日期"""
    return TimezoneUtils.get_china_date()

# 环境变量设置（确保整个应用使用中国时区）
os.environ.setdefault('TZ', 'Asia/Shanghai')