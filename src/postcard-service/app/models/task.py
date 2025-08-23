from pydantic import BaseModel
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

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
    metadata: Dict[str, Any] = {}

class PostcardRequest(BaseModel):
    user_input: str
    style: Optional[str] = None
    theme: Optional[str] = None
    user_id: Optional[str] = None

class PostcardResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    concept: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    frontend_code: Optional[str] = None
    preview_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0