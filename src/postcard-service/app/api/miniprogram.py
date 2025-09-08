from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import os

from ..database.connection import get_db
from ..models.task import PostcardRequest, PostcardResponse, TaskStatusResponse, TaskStatus
from ..services.postcard_service import PostcardService

# 设置日志（模块级）
logger = logging.getLogger(__name__)

# 本地安全适配：使用 JWT 校验或请求头识别用户，避免跨服务导入
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "ai-postcard-secret-key-2025")
JWT_ALG = "HS256"

class CurrentUser:
    def __init__(self, user_id: str | None = None, role: str = "user", permissions: Optional[set] = None, session_id: Optional[str] = None):
        self.user_id = user_id
        self.role = role
        self.permissions = permissions or set()
        self.session_id = session_id
    
    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or self.role == "admin"

async def get_current_user(request: Request | None = None) -> CurrentUser:
    if not request:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="缺少请求上下文")
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    if not token:
        token = request.headers.get("x-access-token")
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="缺少身份验证令牌")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload.get("user_id")
        if not user_id:
            raise JWTError("缺少user_id")
        role = payload.get("role", "user")
        perms = set(payload.get("permissions", []))
        session_id = payload.get("session_id")
        return CurrentUser(user_id=user_id, role=role, permissions=perms, session_id=session_id)
    except JWTError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=f"无效的身份验证令牌: {e}")

def require_permission(permission: str, resource_check: bool = False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从参数或 request.state 中获取用户
            current_user = kwargs.get('current_user')
            if not current_user:
                for a in args:
                    if isinstance(a, CurrentUser):
                        current_user = a
                        break
            if not current_user and 'request' in kwargs and isinstance(kwargs['request'], Request):
                current_user = getattr(kwargs['request'].state, 'user', None)
            
            if isinstance(current_user, CurrentUser):
                if not current_user.has_permission(permission):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=403, detail="权限不足")
            # 未获取到用户时，保持兼容，后续由上游网关控制
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def register_resource_ownership(resource_type: str, resource_id_param: str = "id", owner_id_param: str = "user_id"):
    def decorator(func):
        # 这里保留占位，真实所有权校验由网关或专用服务完成
        return func
    return decorator

def flatten_structured_data(structured_data: dict) -> dict:
    """
    🔧 统一的结构化数据扁平化处理函数
    将嵌套的structured_data转换为扁平字段，避免小程序数据传递丢失问题
    """
    flattened_data = {}
    
    if structured_data and isinstance(structured_data, dict):
        # 只添加非空字段，不设置默认值
        mood = structured_data.get('mood', {})
        if mood.get('primary'):
            flattened_data["mood_primary"] = mood['primary']
        if mood.get('intensity'):
            flattened_data["mood_intensity"] = mood['intensity']
        if mood.get('secondary'):
            flattened_data["mood_secondary"] = mood['secondary']
        if mood.get('color_theme'):
            flattened_data["mood_color_theme"] = mood['color_theme']
        
        # 标题
        if structured_data.get('title'):
            flattened_data["card_title"] = structured_data['title']
        
        # 视觉样式
        visual = structured_data.get('visual', {}).get('style_hints', {})
        if visual.get('color_scheme'):
            flattened_data["visual_color_scheme"] = visual['color_scheme']
        if visual.get('layout_style'):
            flattened_data["visual_layout_style"] = visual['layout_style']
        if visual.get('animation_type'):
            flattened_data["visual_animation_type"] = visual['animation_type']
        
        bg_url = structured_data.get('visual', {}).get('background_image_url')
        if bg_url:
            flattened_data["visual_background_image"] = bg_url
        
        # 内容
        content = structured_data.get('content', {})
        if content.get('main_text'):
            flattened_data["content_main_text"] = content['main_text']
        
        quote = content.get('quote', {})
        if quote.get('text'):
            flattened_data["content_quote_text"] = quote['text']
        if quote.get('author'):
            flattened_data["content_quote_author"] = quote['author']
        if quote.get('translation'):
            flattened_data["content_quote_translation"] = quote['translation']
        
        hot_topics = content.get('hot_topics', {})
        if hot_topics.get('douyin'):
            flattened_data["content_hot_topics_douyin"] = hot_topics['douyin']
        if hot_topics.get('xiaohongshu'):
            flattened_data["content_hot_topics_xiaohongshu"] = hot_topics['xiaohongshu']
        
        # 上下文
        context = structured_data.get('context', {})
        if context.get('weather'):
            flattened_data["context_weather"] = context['weather']
        if context.get('location'):
            flattened_data["context_location"] = context['location']  
        if context.get('time_context'):
            flattened_data["context_time"] = context['time_context']
        
        # 处理推荐内容
        recommendations = structured_data.get('recommendations', {})
        if recommendations.get('music') and len(recommendations['music']) > 0:
            music = recommendations['music'][0]
            flattened_data.update({
                "recommendations_music_title": music.get('title', ''),
                "recommendations_music_artist": music.get('artist', ''),
                "recommendations_music_reason": music.get('reason', ''),
            })
        
        if recommendations.get('book') and len(recommendations['book']) > 0:
            book = recommendations['book'][0]
            flattened_data.update({
                "recommendations_book_title": book.get('title', ''),
                "recommendations_book_author": book.get('author', ''),
                "recommendations_book_reason": book.get('reason', ''),
            })
        
        if recommendations.get('movie') and len(recommendations['movie']) > 0:
            movie = recommendations['movie'][0]
            flattened_data.update({
                "recommendations_movie_title": movie.get('title', ''),
                "recommendations_movie_director": movie.get('director', ''),
                "recommendations_movie_reason": movie.get('reason', ''),
            })
        
        # 🔥 关键新增：8个扩展字段处理（卡片背面内容的核心）
        extras = structured_data.get('extras', {})
        if extras and isinstance(extras, dict):
            extras_fields = ['reflections', 'gratitude', 'micro_actions', 'mood_tips', 
                           'life_insights', 'creative_spark', 'mindfulness', 'future_vision']
            
            for field in extras_fields:
                if field in extras:
                    flat_field_name = f'extras_{field}'
                    flattened_data[flat_field_name] = extras[field]
    
    return flattened_data

router = APIRouter(prefix="/miniprogram")

@router.post("/postcards/create")
@require_permission("postcard:create")
@register_resource_ownership("postcard", "task_id", "user_id")
async def create_miniprogram_postcard(
    request: PostcardRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全创建明信片生成任务"""
    try:
        logger.info(f"🔐 用户 {current_user.user_id} 创建明信片任务: {request.user_input[:50]}...")
        
        # 🔥 强制使用当前用户ID，防止伪造
        request.user_id = current_user.user_id
        
        service = PostcardService(db)
        task_id = await service.create_task(request)
        
        # 记录操作日志
        client_ip = getattr(http_request.client, 'host', 'unknown')
        logger.info(f"✅ 任务创建成功: 用户 {current_user.user_id}, 任务 {task_id}, IP: {client_ip}")
        
        return {
            "code": 0,
            "message": "任务创建成功",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "estimated_time": "2-3分钟",
                "user_id": current_user.user_id  # 返回实际用户ID
            }
        }
    except Exception as e:
        logger.error(f"❌ 创建小程序明信片任务失败: {str(e)}")
        return {
            "code": -1,
            "message": f"创建失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/status/{task_id}")
@require_permission("postcard:read", resource_check=True)
async def get_miniprogram_postcard_status(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全获取明信片任务状态"""
    try:
        logger.debug(f"🔍 用户 {current_user.user_id} 查询任务状态: {task_id}")
        
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
        logger.error(f"❌ 获取小程序任务状态失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取状态失败: {str(e)}",
            "data": None
        }

@router.get("/postcards/result/{id}")
async def get_miniprogram_postcard_result(
    id: str,
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """小程序：获取明信片最终结果（支持任务ID或明信片ID）"""
    try:
        service = PostcardService(db)
        
        # 首先尝试按任务ID查询
        result = await service.get_task_result(id)
        
        # 如果按任务ID找不到，再尝试按明信片ID查询
        if not result:
            result = await service.get_postcard_by_id(id)
            # 确保明信片已完成
            if result and result.status != "completed":
                result = None
        
        if not result:
            return {
                "code": -1,
                "message": "结果不存在",
                "data": None
            }
        
        # 解析小程序组件代码
        miniprogram_component = None
        has_animation = False
        if result.frontend_code:
            try:
                import json
                # 解析小程序组件代码JSON
                component_data = json.loads(result.frontend_code)
                if isinstance(component_data, dict):
                    miniprogram_component = component_data
                    
                    # 检查是否包含动画
                    wxss_code = component_data.get('wxss', '')
                    js_code = component_data.get('js', '')
                    has_animation = any([
                        'animation' in wxss_code,
                        'transform' in wxss_code,
                        'transition' in wxss_code,
                        'wx.createAnimation' in js_code,
                        'setData' in js_code and ('scale' in js_code or 'opacity' in js_code)
                    ])
                    
                    logger.info(f"✅ 成功解析小程序组件，包含动画: {has_animation}")
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"解析小程序组件代码失败: {e}")
                miniprogram_component = None
        
        # 🔧 使用统一的扁平化处理函数
        structured_data = getattr(result, 'structured_data', None) or {}
        flattened_data = flatten_structured_data(structured_data)

        return {
            "code": 0,
            "message": "获取结果成功",
            "data": {
                "postcard_id": result.id,
                "task_id": result.task_id,
                "content": result.content,
                "concept": result.concept,
                "image_url": result.image_url,  # Gemini生成的原图
                "card_image_url": getattr(result, 'card_image_url', None),  # HTML转换后的卡片图片
                "card_html": getattr(result, 'card_html', None),  # HTML源码（可选）
                "structured_data": structured_data,  # 保留原始结构化数据
                
                # 🔧 扁平化的结构化数据字段
                **flattened_data,
                
                # 小程序组件相关信息
                "miniprogram_component": miniprogram_component,  # 小程序组件代码（wxml, wxss, js）
                "component_type": getattr(result, "component_type", "postcard"),  # 组件类型
                "has_animation": has_animation,  # 是否包含动画
                "has_interactive": bool(miniprogram_component),  # 是否包含交互组件
                
                # 兼容性字段（废弃，但暂时保留）
                "frontend_code": result.frontend_code,  # 原始JSON代码，供调试使用
                "preview_url": result.preview_url,
                
                # 元数据
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
@require_permission("postcard:read")
async def get_user_miniprogram_postcards(
    user_id: str = None,
    page: int = 1,
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全获取用户的明信片列表"""
    try:
        # 🔥 强制使用当前用户ID，防止查询他人作品
        actual_user_id = current_user.user_id
        
        logger.info(f"📋 用户 {current_user.user_id} 获取作品列表")
        
        service = PostcardService(db)
        postcards = await service.get_user_postcards(actual_user_id, page, limit)
        
        postcard_list = []
        for postcard in postcards:
            # 检查是否有小程序组件
            has_miniprogram_component = bool(postcard.frontend_code)
            has_animation = False
            
            # 尝试解析组件中是否包含动画
            if postcard.frontend_code:
                try:
                    import json
                    component_data = json.loads(postcard.frontend_code)
                    if isinstance(component_data, dict):
                        wxss_code = component_data.get('wxss', '')
                        has_animation = any([
                            'animation' in wxss_code,
                            'transform' in wxss_code,
                            'transition' in wxss_code
                        ])
                except:
                    pass
            
            # 🔧 使用统一的扁平化处理函数
            structured_data = getattr(postcard, 'structured_data', None) or {}
            flattened_data = flatten_structured_data(structured_data)
            
            # 构建明信片数据，包含扁平化字段
            postcard_data = {
                "id": postcard.id,
                # 返回完整内容，避免前端无法从截断文本中解析JSON
                "content": postcard.content or "",
                # 另外提供预览字段供前端列表场景使用
                "content_preview": (postcard.content[:100] + "...") if postcard.content and len(postcard.content) > 100 else (postcard.content or ""),
                "image_url": postcard.image_url,
                "card_image_url": getattr(postcard, 'card_image_url', None),
                "structured_data": structured_data,  # 保留原始结构化数据
                
                # 🔧 添加扁平化的结构化数据字段
                **flattened_data,
                
                "status": postcard.status,
                "created_at": postcard.created_at.strftime("%Y-%m-%d %H:%M") if postcard.created_at else None,
                "component_type": getattr(postcard, "component_type", "postcard"),
                "has_interactive": has_miniprogram_component,
                "has_animation": has_animation
            }
            
            postcard_list.append(postcard_data)
        
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
@require_permission("postcard:delete", resource_check=True)
async def delete_miniprogram_postcard(
    postcard_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全删除明信片"""
    try:
        logger.info(f"🗑️ 用户 {current_user.user_id} 删除明信片: {postcard_id}")
        
        service = PostcardService(db)
        
        # 🔥 验证明信片存在且属于当前用户
        postcard = await service.get_postcard_by_id(postcard_id)
        if not postcard:
            return {
                "code": -1,
                "message": "明信片不存在",
                "data": None
            }
        
        if postcard.user_id != current_user.user_id:
            logger.warning(f"⚠️ 用户尝试删除他人明信片: user={current_user.user_id}, postcard_owner={postcard.user_id}")
            return {
                "code": -403,
                "message": "无权删除该明信片",
                "data": None
            }
        
        success = await service.delete_postcard(postcard_id)
        
        if not success:
            logger.warning(f"明信片删除操作失败: {postcard_id}")
            return {
                "code": -1,
                "message": "删除操作失败",
                "data": None
            }
        
        logger.info(f"✅ 明信片删除成功: {postcard_id}, 用户: {current_user.user_id}")
        return {
            "code": 0,
            "message": "删除成功",
            "data": {
                "postcard_id": postcard_id,
                "deleted_by": current_user.user_id
            }
        }
    except Exception as e:
        logger.error(f"❌ 删除小程序明信片失败: {str(e)}")
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
        
        # 解析小程序组件代码
        miniprogram_component = None
        has_animation = False
        if postcard.frontend_code:
            try:
                import json
                component_data = json.loads(postcard.frontend_code)
                if isinstance(component_data, dict):
                    miniprogram_component = component_data
                    wxss_code = component_data.get('wxss', '')
                    has_animation = any([
                        'animation' in wxss_code,
                        'transform' in wxss_code,
                        'transition' in wxss_code
                    ])
            except:
                pass
        
        # 🔧 使用统一的扁平化处理函数
        structured_data = getattr(postcard, 'structured_data', None) or {}
        flattened_data = flatten_structured_data(structured_data)
        
        return {
            "code": 0,
            "message": "获取分享明信片成功",
            "data": {
                "id": postcard.id,
                "content": postcard.content,
                "image_url": postcard.image_url,
                "card_image_url": getattr(postcard, 'card_image_url', None),
                "structured_data": structured_data,  # 保留原始结构化数据
                
                # 🔧 添加扁平化的结构化数据字段
                **flattened_data,
                
                "created_at": postcard.created_at.strftime("%Y-%m-%d %H:%M") if postcard.created_at else None,
                "is_public": True,  # 分享的明信片默认公开
                
                # 小程序组件相关信息
                "miniprogram_component": miniprogram_component,
                "component_type": getattr(postcard, "component_type", "postcard"),
                "has_animation": has_animation,
                "has_interactive": bool(miniprogram_component),
                
                # 兼容性字段
                "frontend_code": postcard.frontend_code
            }
        }
    except Exception as e:
        logger.error(f"获取分享小程序明信片失败: {str(e)}")
        return {
            "code": -1,
            "message": f"获取分享明信片失败: {str(e)}",
            "data": None
        }

@router.get("/users/{user_id}/quota")
@require_permission("quota:read", resource_check=True)
async def get_user_generation_quota(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_type: Optional[str] = Header(None)
):
    """🔥 小程序：安全获取用户生成配额信息"""
    try:
        # 🔥 只允许查询自己的配额
        if user_id != current_user.user_id:
            logger.warning(f"⚠️ 用户尝试查询他人配额: user={current_user.user_id}, target={user_id}")
            return {
                "code": -403,
                "message": "无权查询该用户配额",
                "data": None
            }
        
        logger.info(f"📊 用户 {current_user.user_id} 查询配额信息")
        
        service = PostcardService(db)
        quota_service = service._get_quota_service()
        quota_info = await quota_service.check_generation_quota(user_id)
        
        return {
            "code": 0,
            "message": "获取配额信息成功",
            "data": quota_info
        }
    except Exception as e:
        logger.error(f"❌ 获取用户配额失败: {user_id} - {str(e)}")
        return {
            "code": -1,
            "message": f"获取配额失败: {str(e)}",
            "data": None
        }
