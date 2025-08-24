#!/usr/bin/env python3
"""
数据库初始化脚本
"""
import asyncio
import logging
import sys
import os

# 添加app模块到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import create_tables, engine, Base
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

if __name__ == "__main__":
    init_database()