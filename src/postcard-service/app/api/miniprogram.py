from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from ..database.connection import get_db
from ..models.task import PostcardRequest, PostcardResponse, TaskStatusResponse, TaskStatus
from ..services.postcard_service import PostcardService

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/miniprogram")

@router.post("/postcards/create")
async def create_miniprogram_postcard(
    request: PostcardRequest,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：创建明信片生成任务"""
    try:
        logger.info(f"小程序创建明信片任务: {request.user_input[:50]}...")
        
        service = PostcardService(db)
        task_id = await service.create_task(request)
        
        return {
            "code": 0,
            "message": "任务创建成功",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "estimated_time": "2-3分钟"
            }
        }
    except Exception as e:
        logger.error(f"创建小程序明信片任务失败: {str(e)}")
        return {
            "code": -1,
            "message": f"创建失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/status/{task_id}")
async def get_miniprogram_postcard_status(
    task_id: str,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：获取明信片任务状态"""
    try:
        service = PostcardService(db)
        status = await service.get_task_status(task_id)
        
        if not status:
            return {
                "code": -1,
                "message": "任务不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取状态成功",
            "data": {
                "task_id": task_id,
                "status": status.status,
                "error": status.error_message,
                "created_at": status.created_at.isoformat() if status.created_at else None,
                "updated_at": status.updated_at.isoformat() if status.updated_at else None
            }
        }
    except Exception as e:
        logger.error(f"获取小程序任务状态失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取状态失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/result/{task_id}")
async def get_miniprogram_postcard_result(
    task_id: str,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：获取明信片最终结果"""
    try:
        service = PostcardService(db)
        result = await service.get_task_result(task_id)
        
        if not result:
            return {
                "code": -1,
                "message": "结果不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取结果成功",
            "data": {
                "postcard_id": result.id,
                "task_id": task_id,
                "content": result.content,
                "concept": result.concept,
                "image_url": result.image_url,
                "frontend_code": result.frontend_code,
                "preview_url": result.preview_url,
                "status": result.status,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "generation_time": (getattr(result, "generation_time", None) or 0)
            }
        }
    except Exception as e:
        logger.error(f"获取小程序任务结果失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取结果失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/user")
async def get_user_miniprogram_postcards(
    user_id: str,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：获取用户的明信片列表"""
    try:
        service = PostcardService(db)
        postcards = await service.get_user_postcards(user_id, page, limit)
        
        postcard_list = []
        for postcard in postcards:
            postcard_list.append({
                "id": postcard.id,
                "content": postcard.content[:100] + "..." if len(postcard.content) > 100 else postcard.content,
                "image_url": postcard.image_url,
                "status": postcard.status,
                "created_at": postcard.created_at.strftime("%Y-%m-%d %H:%M") if postcard.created_at else None,
                "has_interactive": bool(postcard.frontend_code)
            })
        
        return {
            "code": 0,
            "message": "获取用户作品成功",
            "data": {
                "postcards": postcard_list,
                "page": page,
                "limit": limit,
                "total": len(postcard_list)
            }
        }
    except Exception as e:
        logger.error(f"获取用户小程序作品失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取作品失败: {str(e)}",
            "data": None
        }

@router.delete("/postcards/{postcard_id}")
async def delete_miniprogram_postcard(
    postcard_id: str,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：删除明信片"""
    try:
        service = PostcardService(db)
        success = await service.delete_postcard(postcard_id)
        
        if not success:
            return {
                "code": -1,
                "message": "明信片不存在或已被删除",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "删除成功",
            "data": None
        }
    except Exception as e:
        logger.error(f"删除小程序明信片失败: {str(e)}")
        return {
            "code": -1,
            "message": f"删除失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/share/{postcard_id}")
async def get_shared_miniprogram_postcard(
    postcard_id: str,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：获取分享的明信片详情"""
    try:
        service = PostcardService(db)
        postcard = await service.get_postcard_by_id(postcard_id)
        
        if not postcard:
            return {
                "code": -1,
                "message": "明信片不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取分享明信片成功",
            "data": {
                "id": postcard.id,
                "content": postcard.content,
                "image_url": postcard.image_url,
                "frontend_code": postcard.frontend_code,
                "created_at": postcard.created_at.strftime("%Y-%m-%d %H:%M") if postcard.created_at else None,
                "is_public": True  # 分享的明信片默认公开
            }
        }
    except Exception as e:
        logger.error(f"获取分享小程序明信片失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取分享明信片失败: {str(e)}",
            "data": None
        }