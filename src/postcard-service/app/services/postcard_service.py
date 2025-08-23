import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.postcard import Postcard, TaskStatus
from ..models.task import PostcardGenerationTask, PostcardRequest, TaskStatusResponse
from .queue_service import QueueService

logger = logging.getLogger(__name__)

class PostcardService:
    def __init__(self, db: Session):
        self.db = db
        self.queue_service = QueueService()

    async def create_task(self, request: PostcardRequest) -> str:
        """创建新的明信片生成任务"""
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建数据库记录
            postcard = Postcard(
                task_id=task_id,
                user_id=request.user_id,
                user_input=request.user_input,
                style=request.style,
                theme=request.theme,
                status=TaskStatus.PENDING.value,
                generation_params={
                    "user_input": request.user_input,
                    "style": request.style,
                    "theme": request.theme,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            self.db.add(postcard)
            self.db.commit()
            self.db.refresh(postcard)
            
            # 创建任务消息
            task = PostcardGenerationTask(
                task_id=task_id,
                user_input=request.user_input,
                style=request.style,
                theme=request.theme,
                user_id=request.user_id,
                created_at=datetime.now().isoformat()
            )
            
            # 发布到消息队列
            await self.queue_service.publish_task(task)
            
            logger.info(f"✅ 任务创建成功: {task_id}")
            return task_id
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 数据库错误: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ 创建任务失败: {e}")
            raise

    async def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        """获取任务状态"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.task_id == task_id).first()
            
            if not postcard:
                return None
            
            return TaskStatusResponse(
                task_id=postcard.task_id,
                status=TaskStatus(postcard.status),
                created_at=postcard.created_at,
                updated_at=postcard.updated_at,
                completed_at=postcard.completed_at,
                concept=postcard.concept,
                content=postcard.content,
                image_url=postcard.image_url,
                frontend_code=postcard.frontend_code,
                preview_url=postcard.preview_url,
                error_message=postcard.error_message,
                retry_count=postcard.retry_count
            )
            
        except Exception as e:
            logger.error(f"❌ 获取任务状态失败: {task_id} - {e}")
            raise

    async def update_task_status(self, task_id: str, status: TaskStatus, error_message: Optional[str] = None):
        """更新任务状态"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.task_id == task_id).first()
            
            if not postcard:
                logger.warning(f"⚠️ 任务不存在: {task_id}")
                return False
            
            postcard.status = status.value
            if error_message:
                postcard.error_message = error_message
            
            if status == TaskStatus.COMPLETED:
                postcard.completed_at = datetime.now()
            elif status == TaskStatus.FAILED:
                postcard.retry_count += 1
            
            self.db.commit()
            logger.info(f"✅ 任务状态更新: {task_id} -> {status.value}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 更新任务状态失败: {task_id} - {e}")
            raise

    async def save_intermediate_result(self, task_id: str, step_name: str, result_data: Dict[str, Any]):
        """保存中间结果"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.task_id == task_id).first()
            
            if not postcard:
                logger.warning(f"⚠️ 任务不存在: {task_id}")
                return False
            
            # 根据步骤保存不同的结果
            if step_name == "ConceptGenerator":
                postcard.concept = result_data.get("concept")
            elif step_name == "ContentGenerator":
                postcard.content = result_data.get("content")
            elif step_name == "ImageGenerator":
                postcard.image_url = result_data.get("image_url")
            elif step_name == "FrontendCoder":
                postcard.frontend_code = result_data.get("frontend_code")
                postcard.preview_url = result_data.get("preview_url")
            
            self.db.commit()
            logger.info(f"✅ 中间结果保存成功: {task_id} - {step_name}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 保存中间结果失败: {task_id} - {e}")
            raise

    async def save_final_result(self, task_id: str, results: Dict[str, Any]):
        """保存最终结果"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.task_id == task_id).first()
            
            if not postcard:
                logger.warning(f"⚠️ 任务不存在: {task_id}")
                return False
            
            # 保存所有结果
            if "concept" in results:
                postcard.concept = results["concept"]
            if "content" in results:
                postcard.content = results["content"]
            if "image_url" in results:
                postcard.image_url = results["image_url"]
            if "frontend_code" in results:
                postcard.frontend_code = results["frontend_code"]
            if "preview_url" in results:
                postcard.preview_url = results["preview_url"]
            
            postcard.status = TaskStatus.COMPLETED.value
            postcard.completed_at = datetime.now()
            
            self.db.commit()
            logger.info(f"✅ 最终结果保存成功: {task_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 保存最终结果失败: {task_id} - {e}")
            raise