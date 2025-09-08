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
from .quota_service import QuotaService
from .concurrent_quota_service import ConcurrentSafeQuotaService

logger = logging.getLogger(__name__)

class PostcardService:
    def __init__(self, db: Session):
        self.db = db
        self.queue_service = QueueService()
        self.quota_service = QuotaService(db)
        # 🔥 并发安全配额服务（双模式支持）
        self.concurrent_quota_service = ConcurrentSafeQuotaService(db)
    
    def _get_quota_service(self):
        """获取配额服务实例（优先使用并发安全版本）"""
        import os
        use_concurrent_quota = os.getenv('QUOTA_LOCKS_ENABLED', 'false').lower() == 'true'
        
        if use_concurrent_quota:
            logger.debug("🔒 使用并发安全配额服务")
            return self.concurrent_quota_service
        else:
            logger.debug("🔄 使用传统配额服务")
            return self.quota_service

    async def create_task(self, request: PostcardRequest) -> str:
        """创建新的明信片生成任务"""
        try:
            # 🔥 检查用户每日生成配额（自动选择服务）
            quota_service = self._get_quota_service()
            quota_check = await quota_service.check_generation_quota(request.user_id)
            if not quota_check["can_generate"]:
                raise Exception(f"每日生成次数已用完。{quota_check['message']}")
            
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
            try:
                self.db.commit()
            except SQLAlchemyError as e:
                self.db.rollback()
                err = str(e)
                # 友好提示：数据库未迁移时的典型错误
                if "UndefinedColumn" in err or "card_image_url" in err or "card_html" in err:
                    logger.error("数据库缺少新列，请先执行迁移: sh scripts/dev.sh migrate-db")
                    raise Exception("数据库未迁移：缺少 card_image_url/card_html 等新列。请运行: sh scripts/dev.sh migrate-db")
                raise
            self.db.refresh(postcard)
            
            # 创建任务消息
            task = PostcardGenerationTask(
                task_id=task_id,
                user_input=request.user_input,
                style=request.style,
                theme=request.theme,
                user_id=request.user_id,
                created_at=datetime.now().isoformat(),
                # 🆕 传递base64编码的情绪图片数据
                emotion_image_base64=request.emotion_image_base64
            )
            
            # 发布到消息队列
            await self.queue_service.publish_task(task)
            
            # 🔥 消耗用户配额 - 传递卡片ID（自动选择服务）
            quota_service = self._get_quota_service()
            if hasattr(quota_service, 'consume_generation_quota_safe'):
                # 使用并发安全版本
                await quota_service.consume_generation_quota_safe(request.user_id, postcard.id)
            else:
                # 使用传统版本
                await quota_service.consume_generation_quota(request.user_id, postcard.id)
            
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
            
            # 构建基础响应数据
            response_data = {
                'task_id': postcard.task_id,
                'status': TaskStatus(postcard.status),
                'created_at': postcard.created_at,
                'updated_at': postcard.updated_at,
                'completed_at': postcard.completed_at,
                'concept': postcard.concept,
                'content': postcard.content,
                'image_url': postcard.image_url,
                'frontend_code': postcard.frontend_code,
                'preview_url': postcard.preview_url,
                'card_image_url': getattr(postcard, 'card_image_url', None),
                'card_html': getattr(postcard, 'card_html', None),
                'structured_data': getattr(postcard, 'structured_data', None),
                'error_message': postcard.error_message,
                'retry_count': postcard.retry_count
            }
            
            # 🆕 添加扁平化字段 - 从structured_data中提取
            structured_data = getattr(postcard, 'structured_data', None)
            if structured_data and isinstance(structured_data, dict):
                flattened_fields = self._flatten_structured_data(structured_data)
                response_data.update(flattened_fields)
            
            return TaskStatusResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ 获取任务状态失败: {task_id} - {e}")
            raise

    async def update_task_status(self, task_id: str, status: TaskStatus, error_message: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
        """更新任务状态"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.task_id == task_id).first()
            
            if not postcard:
                logger.warning(f"⚠️ 任务不存在: {task_id}")
                return False
            
            postcard.status = status.value
            if error_message:
                postcard.error_message = error_message
            # 如果传入了需要写入的最终结果字段，一并写入
            if extra:
                if 'concept' in extra:
                    postcard.concept = extra['concept']
                if 'content' in extra:
                    postcard.content = extra['content']
                if 'image_url' in extra:
                    postcard.image_url = extra['image_url']
                if 'frontend_code' in extra:
                    postcard.frontend_code = extra['frontend_code']
                if 'preview_url' in extra:
                    postcard.preview_url = extra['preview_url']
                if 'card_image_url' in extra:
                    postcard.card_image_url = extra['card_image_url']
                if 'card_html' in extra:
                    postcard.card_html = extra['card_html']
                if 'structured_data' in extra:
                    postcard.structured_data = extra['structured_data']
            
            if status == TaskStatus.COMPLETED:
                postcard.completed_at = datetime.now()
            elif status == TaskStatus.FAILED:
                postcard.retry_count += 1
                # 🔥 任务失败时恢复配额，允许用户重新生成（自动选择服务）
                try:
                    quota_service = self._get_quota_service()
                    if hasattr(quota_service, 'handle_task_failure_safe'):
                        # 使用并发安全版本
                        await quota_service.handle_task_failure_safe(postcard.user_id, postcard.id)
                    else:
                        # 使用传统版本
                        await quota_service.handle_task_failure(postcard.user_id, postcard.id)
                    logger.info(f"✅ 任务失败，已恢复配额: {task_id}")
                except Exception as quota_error:
                    logger.error(f"⚠️ 恢复配额失败: {task_id} - {quota_error}")
            
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
            elif step_name == "StructuredContentGenerator":
                postcard.structured_data = result_data.get("structured_data")
            
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
            if "card_image_url" in results:
                postcard.card_image_url = results["card_image_url"]
            if "card_html" in results:
                postcard.card_html = results["card_html"]
            if "structured_data" in results:
                postcard.structured_data = results["structured_data"]
            
            postcard.status = TaskStatus.COMPLETED.value
            postcard.completed_at = datetime.now()
            
            self.db.commit()
            logger.info(f"✅ 最终结果保存成功: {task_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 保存最终结果失败: {task_id} - {e}")
            raise

    async def get_task_result(self, task_id: str) -> Optional[Postcard]:
        """获取任务最终结果"""
        try:
            postcard = self.db.query(Postcard).filter(
                Postcard.task_id == task_id,
                Postcard.status == TaskStatus.COMPLETED.value
            ).first()
            
            return postcard
            
        except Exception as e:
            logger.error(f"❌ 获取任务结果失败: {task_id} - {e}")
            raise

    async def get_user_postcards(self, user_id: str, page: int = 1, limit: int = 10):
        """获取用户的明信片列表"""
        try:
            offset = (page - 1) * limit
            
            postcards = self.db.query(Postcard).filter(
                Postcard.user_id == user_id,
                Postcard.status == TaskStatus.COMPLETED.value
            ).order_by(Postcard.created_at.desc()).offset(offset).limit(limit).all()
            
            return postcards
            
        except Exception as e:
            logger.error(f"❌ 获取用户作品失败: {user_id} - {e}")
            raise

    async def delete_postcard(self, postcard_id: str) -> bool:
        """删除明信片"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.id == postcard_id).first()
            
            if not postcard:
                return False
            
            # 保存用户ID用于配额恢复
            user_id = postcard.user_id
            
            self.db.delete(postcard)
            self.db.commit()
            
            # 🔥 释放今日卡片位置（不恢复生成次数）（自动选择服务）
            quota_service = self._get_quota_service()
            if hasattr(quota_service, 'release_card_position_safe'):
                # 使用并发安全版本
                await quota_service.release_card_position_safe(user_id, postcard_id)
            else:
                # 使用传统版本
                await quota_service.release_card_position(user_id, postcard_id)
            
            logger.info(f"✅ 明信片删除成功: {postcard_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ 删除明信片失败: {postcard_id} - {e}")
            raise

    async def get_postcard_by_id(self, postcard_id: str) -> Optional[Postcard]:
        """根据ID获取明信片"""
        try:
            postcard = self.db.query(Postcard).filter(Postcard.id == postcard_id).first()
            return postcard
            
        except Exception as e:
            logger.error(f"❌ 获取明信片失败: {postcard_id} - {e}")
            raise
    
    def _flatten_structured_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """将structured_data扁平化为协议约定的字段格式"""
        flattened = {}
        
        try:
            # 基础标题
            if 'title' in structured_data:
                flattened['card_title'] = structured_data['title']
            
            # 情绪字段
            mood = structured_data.get('mood', {})
            if isinstance(mood, dict):
                if 'primary' in mood:
                    flattened['mood_primary'] = mood['primary']
                if 'intensity' in mood:
                    flattened['mood_intensity'] = mood['intensity']
                if 'secondary' in mood:
                    flattened['mood_secondary'] = mood['secondary']
                if 'color_theme' in mood:
                    flattened['mood_color_theme'] = mood['color_theme']
            
            # 视觉样式字段
            visual = structured_data.get('visual', {})
            if isinstance(visual, dict):
                style_hints = visual.get('style_hints', {})
                if isinstance(style_hints, dict):
                    if 'color_scheme' in style_hints:
                        flattened['visual_color_scheme'] = style_hints['color_scheme']
                    if 'layout_style' in style_hints:
                        flattened['visual_layout_style'] = style_hints['layout_style']
                    if 'animation_type' in style_hints:
                        flattened['visual_animation_type'] = style_hints['animation_type']
                
                if 'background_image_url' in visual:
                    flattened['visual_background_image'] = visual['background_image_url']
            
            # 内容字段
            content = structured_data.get('content', {})
            if isinstance(content, dict):
                if 'main_text' in content:
                    flattened['content_main_text'] = content['main_text']
                
                quote = content.get('quote', {})
                if isinstance(quote, dict):
                    if 'text' in quote:
                        flattened['content_quote_text'] = quote['text']
                    if 'author' in quote:
                        flattened['content_quote_author'] = quote['author']
                    if 'translation' in quote:
                        flattened['content_quote_translation'] = quote['translation']
                
                hot_topics = content.get('hot_topics', {})
                if isinstance(hot_topics, dict):
                    if 'douyin' in hot_topics:
                        flattened['content_hot_topics_douyin'] = hot_topics['douyin']
                    if 'xiaohongshu' in hot_topics:
                        flattened['content_hot_topics_xiaohongshu'] = hot_topics['xiaohongshu']
            
            # 上下文字段
            context = structured_data.get('context', {})
            if isinstance(context, dict):
                if 'weather' in context:
                    flattened['context_weather'] = context['weather']
                if 'location' in context:
                    flattened['context_location'] = context['location']
                if 'time_context' in context:
                    flattened['context_time'] = context['time_context']
            
            # 推荐内容字段
            recommendations = structured_data.get('recommendations', {})
            if isinstance(recommendations, dict):
                # 音乐推荐
                music = recommendations.get('music', [])
                if music and len(music) > 0:
                    music_item = music[0] if isinstance(music, list) else music
                    if isinstance(music_item, dict):
                        if 'title' in music_item:
                            flattened['recommendations_music_title'] = music_item['title']
                        if 'artist' in music_item:
                            flattened['recommendations_music_artist'] = music_item['artist']
                        if 'reason' in music_item:
                            flattened['recommendations_music_reason'] = music_item['reason']
                
                # 书籍推荐
                book = recommendations.get('book', [])
                if book and len(book) > 0:
                    book_item = book[0] if isinstance(book, list) else book
                    if isinstance(book_item, dict):
                        if 'title' in book_item:
                            flattened['recommendations_book_title'] = book_item['title']
                        if 'author' in book_item:
                            flattened['recommendations_book_author'] = book_item['author']
                        if 'reason' in book_item:
                            flattened['recommendations_book_reason'] = book_item['reason']
                
                # 电影推荐
                movie = recommendations.get('movie', [])
                if movie and len(movie) > 0:
                    movie_item = movie[0] if isinstance(movie, list) else movie
                    if isinstance(movie_item, dict):
                        if 'title' in movie_item:
                            flattened['recommendations_movie_title'] = movie_item['title']
                        if 'director' in movie_item:
                            flattened['recommendations_movie_director'] = movie_item['director']
                        if 'reason' in movie_item:
                            flattened['recommendations_movie_reason'] = movie_item['reason']
            
            # 🆕 扩展字段处理 - 8个extras字段（卡片背面内容的核心）
            extras = structured_data.get('extras', {})
            if isinstance(extras, dict):
                extras_fields = ['reflections', 'gratitude', 'micro_actions', 'mood_tips', 
                               'life_insights', 'creative_spark', 'mindfulness', 'future_vision']
                
                for field in extras_fields:
                    if field in extras:
                        flat_field_name = f'extras_{field}'
                        flattened[flat_field_name] = extras[field]
            
            logger.info(f"📊 扁平化数据完成，生成字段: {list(flattened.keys())}")
            
        except Exception as e:
            logger.error(f"❌ 数据扁平化失败: {e}")
            # 返回空字典，不影响主要功能
        
        return flattened