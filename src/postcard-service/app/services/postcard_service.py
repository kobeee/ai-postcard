import uuid
import json
import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

# 添加common模块路径并导入时区工具
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
try:
    from common.timezone_utils import china_now
except ImportError:
    def china_now():
        return datetime.now(ZoneInfo("Asia/Shanghai"))
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
                    "quiz_answers": [answer.dict() for answer in (request.quiz_answers or [])],
                    "has_quiz_data": len(request.quiz_answers or []) > 0,
                    "created_at": china_now().isoformat()
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
                created_at=china_now().isoformat(),
                # 🆕 传递base64编码的情绪图片数据
                emotion_image_base64=request.emotion_image_base64,
                # 🔮 传递心象签问答数据
                quiz_answers=request.quiz_answers or []
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
                postcard.completed_at = china_now()
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
        """将structured_data扁平化为协议约定的字段格式 - 心象签版本"""
        flattened = {}
        
        try:
            # 🔮 心象签核心数据扁平化
            
            # oracle_theme - 签象主题
            oracle_theme = structured_data.get('oracle_theme', {})
            if isinstance(oracle_theme, dict):
                flattened['oracle_title'] = oracle_theme.get('title', '')
                flattened['oracle_subtitle'] = oracle_theme.get('subtitle', '')
            
            # charm_identity - 签体身份（新增）
            charm_identity = structured_data.get('charm_identity', {})
            if isinstance(charm_identity, dict):
                flattened['charm_name'] = charm_identity.get('charm_name', '')
                flattened['charm_description'] = charm_identity.get('charm_description', '')
                flattened['charm_blessing'] = charm_identity.get('charm_blessing', '')
                flattened['charm_main_color'] = charm_identity.get('main_color', '#8B7355')
                flattened['charm_accent_color'] = charm_identity.get('accent_color', '#D4AF37')
            
            # affirmation - 祝福短句
            if 'affirmation' in structured_data:
                flattened['oracle_affirmation'] = structured_data['affirmation']
            
            # oracle_manifest - 卦象显化
            oracle_manifest = structured_data.get('oracle_manifest', {})
            if isinstance(oracle_manifest, dict):
                # 卦象信息
                hexagram = oracle_manifest.get('hexagram', {})
                if isinstance(hexagram, dict):
                    flattened['oracle_hexagram_name'] = hexagram.get('name', '')
                    flattened['oracle_hexagram_symbol'] = hexagram.get('symbol', '')
                    flattened['oracle_hexagram_insight'] = hexagram.get('insight', '')
                
                # 生活指引
                daily_guide = oracle_manifest.get('daily_guide', [])
                if isinstance(daily_guide, list):
                    flattened['oracle_daily_guides'] = daily_guide
                    # 同时提供单独的字段便于前端使用
                    for i, guide in enumerate(daily_guide[:3]):  # 最多3条
                        flattened[f'oracle_daily_guide_{i+1}'] = guide
                
                # 风水关注点
                flattened['oracle_fengshui_focus'] = oracle_manifest.get('fengshui_focus', '')
                
                # 仪式提示
                flattened['oracle_ritual_hint'] = oracle_manifest.get('ritual_hint', '')
                
                # 五行平衡
                element_balance = oracle_manifest.get('element_balance', {})
                if isinstance(element_balance, dict):
                    for element in ['wood', 'fire', 'earth', 'metal', 'water']:
                        flattened[f'oracle_element_{element}'] = element_balance.get(element, 0.5)
            
            # ink_reading - 墨迹解读
            ink_reading = structured_data.get('ink_reading', {})
            if isinstance(ink_reading, dict):
                flattened['oracle_stroke_impression'] = ink_reading.get('stroke_impression', '')
                
                # 象征关键词
                symbolic_keywords = ink_reading.get('symbolic_keywords', [])
                if isinstance(symbolic_keywords, list):
                    flattened['oracle_symbolic_keywords'] = symbolic_keywords
                    # 提供单独字段
                    for i, keyword in enumerate(symbolic_keywords[:3]):  # 最多3个
                        flattened[f'oracle_symbolic_keyword_{i+1}'] = keyword
                
                # 墨迹指标
                ink_metrics = ink_reading.get('ink_metrics', {})
                if isinstance(ink_metrics, dict):
                    flattened['oracle_stroke_count'] = ink_metrics.get('stroke_count', 0)
                    flattened['oracle_dominant_quadrant'] = ink_metrics.get('dominant_quadrant', 'center')
                    flattened['oracle_pressure_tendency'] = ink_metrics.get('pressure_tendency', 'steady')
            
            # context_insights - 上下文洞察
            context_insights = structured_data.get('context_insights', {})
            if isinstance(context_insights, dict):
                flattened['oracle_session_time'] = context_insights.get('session_time', '')
                flattened['oracle_season_hint'] = context_insights.get('season_hint', '')
                flattened['oracle_visit_pattern'] = context_insights.get('visit_pattern', '')
                
                # 历史关键词
                historical_keywords = context_insights.get('historical_keywords', [])
                if isinstance(historical_keywords, list):
                    flattened['oracle_historical_keywords'] = historical_keywords
            
            # blessing_stream - 祝福流
            blessing_stream = structured_data.get('blessing_stream', [])
            if isinstance(blessing_stream, list):
                flattened['oracle_blessing_stream'] = blessing_stream
                # 提供单独字段便于前端使用
                for i, blessing in enumerate(blessing_stream[:6]):  # 最多6个
                    flattened[f'oracle_blessing_{i+1}'] = blessing
            
            # art_direction - 艺术指导
            art_direction = structured_data.get('art_direction', {})
            if isinstance(art_direction, dict):
                flattened['oracle_image_prompt'] = art_direction.get('image_prompt', '')
                
                # 调色板
                palette = art_direction.get('palette', [])
                if isinstance(palette, list):
                    flattened['oracle_palette'] = palette
                    # 提供单独颜色字段
                    for i, color in enumerate(palette[:3]):  # 最多3个主色
                        flattened[f'oracle_color_{i+1}'] = color
                
                flattened['oracle_animation_hint'] = art_direction.get('animation_hint', '')
            
            # culture_note - 文化说明
            if 'culture_note' in structured_data:
                flattened['oracle_culture_note'] = structured_data['culture_note']
            
            # 🔮 ai_selected_charm - AI选择的签体信息
            ai_selected_charm = structured_data.get('ai_selected_charm', {})
            if isinstance(ai_selected_charm, dict):
                flattened['ai_selected_charm_id'] = ai_selected_charm.get('charm_id', '')
                flattened['ai_selected_charm_name'] = ai_selected_charm.get('charm_name', '')
                flattened['ai_selected_charm_reasoning'] = ai_selected_charm.get('ai_reasoning', '')
            
            # 🔄 兼容性处理：保留旧数据结构的部分字段以便渐进式迁移
            # 如果同时存在旧结构，优先使用新结构但保留旧字段便于过渡
            
            # 旧结构 - 情绪字段（兼容）
            mood = structured_data.get('mood', {})
            if isinstance(mood, dict) and mood:
                if 'primary' in mood:
                    flattened['mood_primary'] = mood['primary']
                if 'intensity' in mood:
                    flattened['mood_intensity'] = mood['intensity']
            
            # 旧结构 - 视觉字段（兼容）
            visual = structured_data.get('visual', {})
            if isinstance(visual, dict) and visual:
                if 'background_image_url' in visual:
                    flattened['visual_background_image'] = visual['background_image_url']
            
            logger.info(f"📊 心象签数据扁平化完成，生成字段: {list(flattened.keys())}")
            
        except Exception as e:
            logger.error(f"❌ 心象签数据扁平化失败: {e}")
            # 返回空字典，不影响主要功能
        
        return flattened