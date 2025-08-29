"""
HTML转图片API - 为小程序提供HTML内容的图片渲染服务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..services.html_to_image import HTMLToImageService

logger = logging.getLogger(__name__)

router = APIRouter()

class HTMLToImageRequest(BaseModel):
    html_content: str
    width: Optional[int] = 375
    height: Optional[int] = 600
    format: Optional[str] = "png"
    filename: Optional[str] = None

class HTMLToImageResponse(BaseModel):
    success: bool
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    fallback: Optional[bool] = False
    error: Optional[str] = None

# 初始化HTML转图片服务
html_to_image_service = HTMLToImageService()

@router.post("/html-to-image", response_model=HTMLToImageResponse)
async def convert_html_to_image(request: HTMLToImageRequest):
    """
    将HTML内容转换为图片
    专为小程序无法使用web-view时的替代方案
    """
    try:
        logger.info(f"📸 HTML转图片请求: {request.width}x{request.height}, 内容长度: {len(request.html_content)}")
        
        result = await html_to_image_service.convert_html_to_image(
            html_content=request.html_content,
            output_filename=request.filename,
            width=request.width,
            height=request.height,
            format=request.format
        )
        
        if result:
            logger.info(f"✅ HTML转图片成功: {result.get('image_url')}")
            return HTMLToImageResponse(**result)
        else:
            logger.error("❌ HTML转图片失败")
            raise HTTPException(status_code=500, detail="HTML转图片失败")
            
    except Exception as e:
        logger.error(f"❌ HTML转图片API异常: {e}")
        return HTMLToImageResponse(
            success=False,
            error=str(e)
        )

@router.get("/html-to-image/{filename}")
async def get_image_info(filename: str):
    """获取图片信息"""
    try:
        info = await html_to_image_service.get_image_info(filename)
        if info:
            return info
        else:
            raise HTTPException(status_code=404, detail="图片不存在")
    except Exception as e:
        logger.error(f"获取图片信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取图片信息失败")

@router.delete("/html-to-image/cleanup")
async def cleanup_old_images(max_age_hours: int = 24):
    """清理旧图片文件"""
    try:
        await html_to_image_service.cleanup_old_images(max_age_hours)
        return {"message": f"已清理超过{max_age_hours}小时的旧图片"}
    except Exception as e:
        logger.error(f"清理旧图片失败: {e}")
        raise HTTPException(status_code=500, detail="清理旧图片失败")

@router.get("/html-to-image/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "html-to-image",
        "supported_formats": ["png", "jpg", "svg"],
        "max_dimensions": {"width": 1920, "height": 1080}
    }