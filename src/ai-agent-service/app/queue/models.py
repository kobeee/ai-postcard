from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum

class TaskType(str, Enum):
    POSTCARD_GENERATION = "postcard_generation"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PostcardGenerationTask(BaseModel):
    task_id: str
    task_type: TaskType = TaskType.POSTCARD_GENERATION
    user_input: str
    style: Optional[str] = None
    theme: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str
    # 🆕 版本3.0新增：直接包含base64编码的情绪图片数据
    emotion_image_base64: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)