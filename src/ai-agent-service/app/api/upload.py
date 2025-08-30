"""
上传API - 处理情绪图片上传
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import os
import uuid
from typing import Dict, Any
import aiofiles
from PIL import Image
import io

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()

# 配置上传目录
UPLOAD_DIR = "/app/app/static/generated/emotions"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 支持的图片格式
ALLOWED_FORMATS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """简单的token验证（实际项目中应该验证JWT）"""
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Token缺失")
    
    # 这里应该验证token的有效性，暂时简单检查存在性
    # 在实际项目中，应该验证JWT token并获取用户信息
    logger.info(f"Token验证通过: {token[:10]}...")
    return {"user_id": "authenticated_user"}

@router.post("/emotion-image-base64")
async def upload_emotion_image_base64(request: dict, user_info: Dict = Depends(verify_token)) -> Dict[str, Any]:
    """
    上传情绪墨迹图片（base64格式）
    
    Args:
        request: 包含base64数据的请求 {"image_base64": "...", "format": "png", "size": 12345}
        user_info: 用户信息（通过token验证获取）
    
    Returns:
        包含图片URL和元信息的字典
    """
    try:
        logger.info(f"开始处理base64情绪图片上传, 用户: {user_info}")
        
        # 获取base64数据
        image_base64 = request.get('image_base64')
        image_format = request.get('format', 'png').lower()
        estimated_size = request.get('size', 0)
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="缺少base64图片数据")
        
        # 验证base64数据
        try:
            import base64
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            logger.error(f"base64解码失败: {e}")
            raise HTTPException(status_code=400, detail="无效的base64数据")
        
        # 检查文件大小
        actual_size = len(image_bytes)
        if actual_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件大小超过限制({MAX_FILE_SIZE/1024/1024}MB)")
        
        # 验证是否为有效图片
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # 验证图片完整性
        except Exception as e:
            logger.error(f"图片验证失败: {e}")
            raise HTTPException(status_code=400, detail="无效的图片数据")
        
        # 生成唯一文件名
        unique_filename = f"emotion_{uuid.uuid4().hex[:12]}.{image_format}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(image_bytes)
        
        # 构建可访问的URL  
        base_url = os.getenv("AI_AGENT_PUBLIC_URL", "http://ai-agent-service:8000")
        image_url = f"{base_url}/static/generated/emotions/{unique_filename}"
        
        # 获取图片基本信息
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        result = {
            "success": True,
            "data": {
                "image_url": image_url,
                "filename": unique_filename,
                "size": actual_size,
                "dimensions": {
                    "width": width,
                    "height": height
                },
                "format": image_format.upper(),
                "upload_time": "2025-08-30T16:00:00Z",  # 实际项目中使用当前时间
                "source": "base64_upload"
            }
        }
        
        logger.info(f"base64情绪图片上传成功: {image_url}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传base64情绪图片时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/emotion-image")
async def upload_emotion_image(
    emotion_image: UploadFile = File(...),
    user_info: Dict = Depends(verify_token)
) -> Dict[str, Any]:
    """
    上传情绪墨迹图片
    
    Args:
        emotion_image: 上传的图片文件
        user_info: 用户信息（通过token验证获取）
    
    Returns:
        包含图片URL和元信息的字典
    """
    try:
        logger.info(f"开始处理情绪图片上传, 文件名: {emotion_image.filename}")
        
        # 验证文件
        if not emotion_image.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检查文件大小
        content = await emotion_image.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件大小超过限制({MAX_FILE_SIZE/1024/1024}MB)")
        
        # 检查文件格式
        file_extension = emotion_image.filename.split('.')[-1].lower()
        if file_extension not in ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式，支持格式: {ALLOWED_FORMATS}")
        
        # 验证是否为有效图片
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # 验证图片完整性
        except Exception as e:
            logger.error(f"图片验证失败: {e}")
            raise HTTPException(status_code=400, detail="无效的图片文件")
        
        # 生成唯一文件名
        unique_filename = f"emotion_{uuid.uuid4().hex[:12]}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # 构建可访问的URL
        base_url = os.getenv("AI_AGENT_PUBLIC_URL", "http://ai-agent-service:8000")
        image_url = f"{base_url}/static/generated/emotions/{unique_filename}"
        
        # 获取图片基本信息
        image = Image.open(io.BytesIO(content))
        width, height = image.size
        
        result = {
            "success": True,
            "data": {
                "image_url": image_url,
                "filename": unique_filename,
                "original_name": emotion_image.filename,
                "size": len(content),
                "dimensions": {
                    "width": width,
                    "height": height
                },
                "format": file_extension.upper(),
                "upload_time": "2024-08-30T12:00:00Z"  # 实际项目中使用当前时间
            }
        }
        
        logger.info(f"情绪图片上传成功: {image_url}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传情绪图片时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/emotion-image/{filename}")
async def get_emotion_image_info(filename: str) -> Dict[str, Any]:
    """
    获取情绪图片信息
    
    Args:
        filename: 图片文件名
        
    Returns:
        图片信息
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 获取文件信息
        stat = os.stat(file_path)
        
        # 获取图片尺寸
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format_name = img.format
        except Exception:
            width, height, format_name = None, None, None
        
        base_url = os.getenv("AI_AGENT_PUBLIC_URL", "http://ai-agent-service:8000")
        image_url = f"{base_url}/static/generated/emotions/{filename}"
        
        return {
            "success": True,
            "data": {
                "filename": filename,
                "image_url": image_url,
                "size": stat.st_size,
                "dimensions": {
                    "width": width,
                    "height": height
                } if width and height else None,
                "format": format_name,
                "created_time": stat.st_ctime
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片信息时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")