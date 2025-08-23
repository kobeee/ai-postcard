from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum
import uuid

Base = declarative_base()

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Postcard(Base):
    __tablename__ = "postcards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=True)  # 可选用户ID
    status = Column(String, nullable=False, default=TaskStatus.PENDING.value, index=True)
    
    # 用户输入
    user_input = Column(Text, nullable=False)
    style = Column(String(100), nullable=True)
    theme = Column(String(100), nullable=True)
    
    # AI生成的中间结果
    concept = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # 最终结果
    frontend_code = Column(Text, nullable=True)
    preview_url = Column(String(500), nullable=True)
    
    # 生成参数
    generation_params = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)