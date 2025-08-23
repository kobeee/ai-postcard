from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database.connection import get_db
from ..models.task import PostcardRequest, PostcardResponse, TaskStatusResponse, TaskStatus
from ..services.postcard_service import PostcardService

router = APIRouter()

@router.post("/create", response_model=PostcardResponse)
async def create_postcard(
    request: PostcardRequest,
    db: Session = Depends(get_db)
):
    """创建明信片生成任务"""
    try:
        service = PostcardService(db)
        task_id = await service.create_task(request)
        
        return PostcardResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="任务创建成功，正在处理中"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_postcard_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取明信片任务状态"""
    try:
        service = PostcardService(db)
        status = await service.get_task_status(task_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.post("/status/{task_id}")
async def update_postcard_status(
    task_id: str,
    status: TaskStatus,
    error_message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """更新明信片任务状态（内部API）"""
    try:
        service = PostcardService(db)
        success = await service.update_task_status(task_id, status, error_message)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {"message": "状态更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新状态失败: {str(e)}")