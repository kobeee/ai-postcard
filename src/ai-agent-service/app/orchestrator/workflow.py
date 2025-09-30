import asyncio
import logging
import httpx
import os
import json
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PostcardWorkflow:
    """明信片生成工作流编排器"""
    
    def __init__(self):
        self.postcard_service_url = os.getenv("POSTCARD_SERVICE_URL", "http://postcard-service:8000")
        self.logger = logging.getLogger(self.__class__.__name__)
        # 用于跨服务认证的内部服务令牌
        self.internal_service_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
        
        # 将在子类中初始化工作流步骤
        self.steps = []
    
    async def execute(self, task_data: Dict[str, Any]):
        """执行完整的明信片生成工作流 - 支持新旧版本切换"""
        task_id = task_data.get("task_id")
        user_id = task_data.get("user_id")  # 🆕 提取user_id

        context = {
            "task": task_data,
            "results": {},
            "user_id": user_id  # 🆕 注入到context中
        }
        
        # 获取工作流版本配置
        workflow_version = os.getenv("WORKFLOW_VERSION", "two_stage")  # "legacy" | "unified" | "two_stage"
        
        try:
            await asyncio.shield(self.update_task_status(task_id, "processing"))
            
            # 💫 心象签精准感应信号采集和处理
            await self.collect_precision_signals(task_data)
            
            if workflow_version == "two_stage":
                # 🆕 两段式工作流 (2次文本 + 1次生图)
                self.logger.info(f"🚀 使用两段式工作流: {task_id}")
                await self._execute_two_stage_workflow(context)
            elif workflow_version == "unified":
                # 统一工作流 (1次文本 + 1次生图)
                self.logger.info(f"🚀 使用优化版工作流: {task_id}")
                await self._execute_unified_workflow(context)
            else:
                # 传统工作流 (3次文本 + 1次生图)  
                self.logger.info(f"🔄 使用传统版工作流: {task_id}")
                await self._execute_legacy_workflow(context)
            
            # 保存最终结果
            await asyncio.shield(self.save_final_result(task_id, context["results"]))
            await asyncio.shield(self.update_task_status(task_id, "completed"))
            
            self.logger.info(f"🎉 工作流执行完成: {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 工作流执行失败: {task_id} - {e}")
            await self._handle_workflow_failure(task_id, e, context)

    async def _execute_unified_workflow(self, context):
        """执行优化版统一工作流"""
        
        # 步骤1：统一内容生成（整合原有3步）
        from .steps.unified_content_generator import UnifiedContentGenerator
        unified_generator = UnifiedContentGenerator()
        context = await unified_generator.execute(context)
        
        # 步骤2：图像生成
        from .steps.image_generator import ImageGenerator
        image_generator = ImageGenerator()
        context = await image_generator.execute(context)
        
        return context

    async def _execute_two_stage_workflow(self, context):
        """执行两段式工作流"""
        
        # 阶段1：用户洞察分析
        from .steps.two_stage_analyzer import TwoStageAnalyzer
        analyzer = TwoStageAnalyzer()
        context = await analyzer.execute(context)
        
        # 阶段2：心象签生成
        from .steps.two_stage_generator import TwoStageGenerator
        generator = TwoStageGenerator()
        context = await generator.execute(context)
        
        # 阶段3：图像生成
        from .steps.image_generator import ImageGenerator
        image_generator = ImageGenerator()
        context = await image_generator.execute(context)
        
        return context

    async def _execute_legacy_workflow(self, context):
        """执行传统版工作流（保留作为回滚方案）"""
        
        # 原有的4步工作流逻辑保持不变
        from .steps.concept_generator import ConceptGenerator
        from .steps.content_generator import ContentGenerator  
        from .steps.image_generator import ImageGenerator
        from .steps.structured_content_generator import StructuredContentGenerator
        
        steps = [
            ConceptGenerator(),                 # 第1步：概念生成
            ContentGenerator(),                 # 第2步：文案生成  
            ImageGenerator(),                   # 第3步：图片生成
            StructuredContentGenerator()        # 第4步：结构化内容生成（最终步）
        ]
        
        # 🔒 容错执行各个步骤
        completed_steps = 0
        critical_failures = []
        
        for i, step in enumerate(steps, 1):
            step_name = step.__class__.__name__
            self.logger.info(f"📍 执行步骤 {i}/4: {step_name}")
            
            try:
                context = await step.execute(context)
                
                # 保存中间结果
                await self.save_intermediate_result(context["task"].get("task_id"), step_name, context["results"])
                
                self.logger.info(f"✅ 步骤 {i}/4 完成: {step_name}")
                completed_steps += 1
                
            except Exception as e:
                self.logger.error(f"❌ 步骤 {i}/4 失败: {step_name} - {e}")
                
                # 🔒 根据步骤重要性决定是否继续
                if await self._handle_step_failure(step_name, i, e, context):
                    self.logger.warning(f"⚠️ 步骤 {step_name} 失败但已使用fallback，继续执行")
                    completed_steps += 1
                else:
                    critical_failures.append(f"步骤{i}-{step_name}: {str(e)}")
                    # 🔒 如果是关键步骤失败，尝试使用完整fallback
                    if i <= 2:  # 概念生成或文案生成失败
                        context["results"] = await self._get_emergency_fallback(context["task"])
                        self.logger.warning(f"⚠️ 关键步骤 {step_name} 失败，使用紧急fallback")
                        break
                    else:
                        # 非关键步骤失败，继续执行剩余步骤
                        continue
        
        # 🔒 最终检查和兜底
        if completed_steps == 0:
            # 所有步骤都失败，使用紧急fallback
            context["results"] = await self._get_emergency_fallback(context["task"])
            self.logger.error(f"🚨 所有步骤失败，使用紧急fallback: {critical_failures}")
        elif "structured_data" not in context["results"]:
            # 没有结构化数据，补充默认的心象签结构
            context["results"]["structured_data"] = await self._get_default_oracle_structure(context["task"])
            self.logger.warning("⚠️ 缺少结构化数据，补充默认心象签结构")
        
        return context
    
    async def _handle_workflow_failure(self, task_id: str, error: Exception, context: Dict[str, Any]):
        """处理工作流失败"""
        # 🔒 最后的兜底处理
        try:
            fallback_results = await self._get_emergency_fallback(context["task"])
            await asyncio.shield(self.save_final_result(task_id, fallback_results))
            await asyncio.shield(self.update_task_status(task_id, "completed"))
            self.logger.warning(f"⚠️ 工作流异常但已使用紧急fallback完成: {task_id}")
        except Exception as fallback_error:
            self.logger.error(f"🚨 紧急fallback也失败: {fallback_error}")
            try:
                await asyncio.shield(self.update_task_status(task_id, "failed", str(error)))
            except Exception:
                pass
            raise
            
        except Exception as e:
            self.logger.error(f"❌ 工作流执行失败: {task_id} - {e}")
            
            # 🔒 最后的兜底处理
            try:
                fallback_results = await self._get_emergency_fallback(task_data)
                await asyncio.shield(self.save_final_result(task_id, fallback_results))
                await asyncio.shield(self.update_task_status(task_id, "completed"))
                self.logger.warning(f"⚠️ 工作流异常但已使用紧急fallback完成: {task_id}")
            except Exception as fallback_error:
                self.logger.error(f"🚨 紧急fallback也失败: {fallback_error}")
                try:
                    await asyncio.shield(self.update_task_status(task_id, "failed", str(e)))
                except Exception:
                    pass
                raise
    
    async def update_task_status(self, task_id: str, status: str, error_message: str = None):
        """更新任务状态"""
        try:
            url = f"{self.postcard_service_url}/api/v1/postcards/status/{task_id}"
            data = {"status": status}
            if error_message:
                data["error_message"] = error_message

            # 增加重试，提升可靠性，延长超时时间适应大模型响应
            headers = {}
            if self.internal_service_token:
                headers["X-Internal-Service-Token"] = self.internal_service_token
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                for attempt in range(3):
                    try:
                        response = await client.post(url, json=data)
                        if response.status_code == 200:
                            self.logger.info(f"✅ 任务状态更新成功: {task_id} -> {status}")
                            return True
                        else:
                            body = None
                            try:
                                body = response.text
                            except Exception:
                                pass
                            self.logger.error(f"❌ 任务状态更新失败: {task_id} - {response.status_code} - {body}")
                    except Exception as req_err:
                        self.logger.error(f"⚠️ 状态更新请求异常(第{attempt+1}次): {task_id} - {req_err}")
                    await asyncio.sleep(1)
            return False

        except Exception as e:
            self.logger.error(f"❌ 更新任务状态异常: {task_id} - {e}")
            return False
    
    async def save_intermediate_result(self, task_id: str, step_name: str, results: Dict[str, Any]):
        """保存中间结果"""
        try:
            # 调用明信片服务保存中间结果
            # 这里可以根据需要实现具体的保存逻辑
            self.logger.info(f"💾 保存中间结果: {task_id} - {step_name}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存中间结果失败: {task_id} - {step_name} - {e}")
    
    async def save_final_result(self, task_id: str, results: Dict[str, Any]):
        """保存最终结果"""
        try:
            # 通过状态更新接口一并提交最终结果
            self.logger.info(f"💾 保存最终结果: {task_id}")
            self.logger.info(f"📊 结果摘要: {list(results.keys())}")

            payload: Dict[str, Any] = {"status": "completed"}
            # 允许的字段（包含结构化数据）
            for key in ["concept", "content", "image_url", "frontend_code", "preview_url", "card_image_url", "card_html", "structured_data"]:
                if key in results and results[key] is not None:
                    payload[key] = results[key]

            url = f"{self.postcard_service_url}/api/v1/postcards/status/{task_id}"
            headers = {}
            if self.internal_service_token:
                headers["X-Internal-Service-Token"] = self.internal_service_token
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    self.logger.info("✅ 最终结果提交成功")
                else:
                    self.logger.error(f"❌ 最终结果提交失败: {resp.status_code} - {resp.text}")

        except Exception as e:
            self.logger.error(f"❌ 保存最终结果失败: {task_id} - {e}")
    
    async def collect_precision_signals(self, task_data: Dict[str, Any]):
        """采集和处理心象签精准感应信号"""
        try:
            self.logger.info("🔮 开始采集心象签精准感应信号")
            
            user_id = task_data.get("user_id")
            
            # 1. 处理ink_metrics（绘画数据）
            drawing_data = task_data.get("drawing_data", {})
            if drawing_data:
                self.logger.info(f"✅ 采集到绘画数据: {len(drawing_data.get('trajectory', []))}个轨迹点")
            
            # 2. 生成context_insights（上下文洞察）
            context_insights = await self.generate_context_insights(task_data)
            task_data["context_insights"] = context_insights
            
            # 3. 获取历史关键词
            if user_id:
                historical_keywords = await self.extract_historical_keywords(user_id)
                task_data["historical_keywords"] = historical_keywords
                self.logger.info(f"✅ 提取历史关键词: {historical_keywords}")
            
            self.logger.info("✅ 精准感应信号采集完成")
            
        except Exception as e:
            self.logger.error(f"❌ 精准感应信号采集失败: {e}")
            # 继续执行，不阻断工作流
    
    async def generate_context_insights(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成上下文洞察数据"""
        try:
            now = datetime.now()
            hour = now.hour
            month = now.month
            
            # 确定时段
            if hour < 6:
                session_time = f"凌晨 {hour:02d}:{now.minute:02d}"
            elif hour < 12:
                session_time = f"上午 {hour:02d}:{now.minute:02d}"
            elif hour < 18:
                session_time = f"下午 {hour:02d}:{now.minute:02d}"
            elif hour < 22:
                session_time = f"傍晚 {hour:02d}:{now.minute:02d}"
            else:
                session_time = f"夜晚 {hour:02d}:{now.minute:02d}"
            
            # 确定季节
            if 3 <= month <= 5:
                season_hint = "春日时分"
            elif 6 <= month <= 8:
                season_hint = "夏日时分"
            elif 9 <= month <= 11:
                season_hint = "秋日时分"
            else:
                season_hint = "冬日时分"
            
            # 访问模式（简化处理，实际应该查询数据库）
            visit_pattern = "今日心象之旅"
            
            context_insights = {
                "session_time": session_time,
                "season_hint": season_hint,
                "visit_pattern": visit_pattern,
                "historical_keywords": task_data.get("historical_keywords", [])
            }
            
            return context_insights
            
        except Exception as e:
            self.logger.error(f"❌ 生成上下文洞察失败: {e}")
            return {
                "session_time": "当下时刻",
                "season_hint": "四季流转",
                "visit_pattern": "心象探索",
                "historical_keywords": []
            }
    
    async def extract_historical_keywords(self, user_id: str) -> list:
        """从用户历史数据中提取关键词"""
        try:
            # 调用postcard服务获取用户历史数据
            url = f"{self.postcard_service_url}/api/v1/postcards/user/{user_id}/history"
            headers = {}
            if self.internal_service_token:
                headers["X-Internal-Service-Token"] = self.internal_service_token
            
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get(url, params={"limit": 5})  # 获取最近5条记录
                
                if response.status_code == 200:
                    data = response.json()
                    postcards = data.get("postcards", [])
                    
                    keywords = []
                    for postcard in postcards:
                        structured_data = postcard.get("structured_data")
                        if structured_data:
                            try:
                                if isinstance(structured_data, str):
                                    structured_data = json.loads(structured_data)
                                
                                # 从不同字段提取关键词
                                if "oracle_theme" in structured_data:
                                    title = structured_data["oracle_theme"].get("title", "")
                                    if title and len(title) < 10:  # 避免过长的标题
                                        keywords.append(title)
                                
                                if "ink_reading" in structured_data:
                                    symbolic_keywords = structured_data["ink_reading"].get("symbolic_keywords", [])
                                    keywords.extend(symbolic_keywords[:2])  # 最多取2个
                                        
                            except Exception:
                                continue
                    
                    # 去重并限制数量
                    unique_keywords = list(dict.fromkeys(keywords))[:3]
                    return unique_keywords
                
        except Exception as e:
            self.logger.error(f"❌ 提取历史关键词失败: {e}")
        
        return []
    
    async def _handle_step_failure(self, step_name: str, step_index: int, error: Exception, context: Dict[str, Any]) -> bool:
        """处理步骤失败，返回True表示可以继续执行，False表示需要中断"""
        try:
            self.logger.warning(f"🔧 处理步骤失败: {step_name}")
            
            # 根据不同步骤提供不同的fallback策略
            if step_name == "ConceptGenerator":
                # 概念生成失败，使用默认概念
                context["results"]["concept"] = json.dumps({
                    "natural_scene": "微风轻抚",
                    "emotion_tone": "宁静",
                    "color_inspiration": "#e8f4fd"
                }, ensure_ascii=False)
                return True
                
            elif step_name == "ContentGenerator":
                # 文案生成失败，使用默认文案
                context["results"]["content"] = json.dumps({
                    "affirmation": "愿你被这个世界温柔以待",
                    "stroke_impression": "笔触温和，内心平静",
                    "symbolic_keywords": ["平和", "流动"],
                    "daily_guide": ["宜静心思考", "宜关爱自己"]
                }, ensure_ascii=False)
                return True
                
            elif step_name == "ImageGenerator":
                # 图片生成失败，使用默认图片URL或跳过
                context["results"]["image_url"] = ""
                self.logger.warning(f"⚠️ 图片生成失败，将使用默认背景")
                return True
                
            elif step_name == "StructuredContentGenerator":
                # 结构化内容生成失败，生成基础心象签结构
                context["results"]["structured_data"] = await self._get_default_oracle_structure(context["task"])
                return True
                
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 处理步骤失败时发生错误: {e}")
            return False
    
    async def _get_emergency_fallback(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取紧急fallback结果 - 确保总是有可用的心象签"""
        try:
            # 从用户输入中提取基本信息
            user_input = task_data.get("user_input", "")
            user_id = task_data.get("user_id", "")
            
            # 分析用户输入中的情绪倾向
            emotion_keywords = {
                "happy": ["开心", "高兴", "愉快", "快乐", "喜悦"],
                "calm": ["平静", "安静", "宁静", "淡然", "从容"],
                "energetic": ["活力", "精力", "动力", "兴奋", "激动"],
                "thoughtful": ["思考", "沉思", "想念", "回忆", "深思"]
            }
            
            detected_emotion = "calm"
            for emotion, keywords in emotion_keywords.items():
                if any(keyword in user_input for keyword in keywords):
                    detected_emotion = emotion
                    break
            
            # 基于检测到的情绪选择合适的fallback
            fallback_options = {
                "happy": {
                    "concept": '{"natural_scene": "春日暖阳", "emotion_tone": "愉悦", "color_inspiration": "#ffeaa7"}',
                    "content": '{"affirmation": "愿快乐如春花绽放", "stroke_impression": "笔触轻快，心情舒展", "symbolic_keywords": ["明亮", "绽放"], "daily_guide": ["宜分享喜悦", "宜感恩当下"]}',
                    "oracle_theme": {"title": "春日暖阳", "subtitle": "今日心象签"},
                    "affirmation": "愿快乐如春花绽放"
                },
                "calm": {
                    "concept": '{"natural_scene": "湖水如镜", "emotion_tone": "宁静", "color_inspiration": "#dfe6e9"}',
                    "content": '{"affirmation": "愿内心如湖水般宁静", "stroke_impression": "笔触平和，心境如水", "symbolic_keywords": ["宁静", "明澈"], "daily_guide": ["宜静心冥想", "宜整理思绪"]}',
                    "oracle_theme": {"title": "湖水如镜", "subtitle": "今日心象签"},
                    "affirmation": "愿内心如湖水般宁静"
                },
                "energetic": {
                    "concept": '{"natural_scene": "破浪前行", "emotion_tone": "活力", "color_inspiration": "#fd79a8"}',
                    "content": '{"affirmation": "愿活力如潮水般涌现", "stroke_impression": "笔触有力，充满动感", "symbolic_keywords": ["动力", "前进"], "daily_guide": ["宜运动锻炼", "宜挑战自己"]}',
                    "oracle_theme": {"title": "破浪前行", "subtitle": "今日心象签"},
                    "affirmation": "愿活力如潮水般涌现"
                },
                "thoughtful": {
                    "concept": '{"natural_scene": "月下思语", "emotion_tone": "深思", "color_inspiration": "#a29bfe"}',
                    "content": '{"affirmation": "愿思考带来智慧光芒", "stroke_impression": "笔触深沉，思绪绵长", "symbolic_keywords": ["深邃", "智慧"], "daily_guide": ["宜独处思考", "宜书写感悟"]}',
                    "oracle_theme": {"title": "月下思语", "subtitle": "今日心象签"},
                    "affirmation": "愿思考带来智慧光芒"
                }
            }
            
            selected = fallback_options.get(detected_emotion, fallback_options["calm"])
            
            return {
                "concept": selected["concept"],
                "content": selected["content"],
                "image_url": "",
                "structured_data": await self._get_default_oracle_structure(task_data, selected["oracle_theme"], selected["affirmation"])
            }
            
        except Exception as e:
            self.logger.error(f"❌ 生成紧急fallback失败: {e}")
            # 最基础的fallback
            return {
                "concept": '{"natural_scene": "微风轻抚", "emotion_tone": "平和"}',
                "content": '{"affirmation": "愿你被这个世界温柔以待"}',
                "image_url": "",
                "structured_data": await self._get_default_oracle_structure(task_data)
            }
    
    async def _get_default_oracle_structure(self, task_data: Dict[str, Any], oracle_theme: Dict = None, affirmation: str = None) -> Dict[str, Any]:
        """获取默认的心象签结构"""
        import datetime
        
        # 获取当前时间信息
        now = datetime.datetime.now()
        hour = now.hour
        month = now.month
        
        if hour < 6:
            session_time = "凌晨"
        elif hour < 12:
            session_time = "上午"
        elif hour < 18:
            session_time = "下午"
        elif hour < 22:
            session_time = "傍晚"
        else:
            session_time = "夜晚"
            
        if 3 <= month <= 5:
            season_hint = "春季时分"
        elif 6 <= month <= 8:
            season_hint = "夏季时分"
        elif 9 <= month <= 11:
            season_hint = "秋季时分"
        else:
            season_hint = "冬季时分"
        
        return {
            "oracle_theme": oracle_theme or {
                "title": "微风轻抚",
                "subtitle": "今日心象签"
            },
            "affirmation": affirmation or "愿你被这个世界温柔以待",
            "oracle_manifest": {
                "hexagram": {
                    "name": "和风细雨",
                    "insight": "生活如细雨，滋润着心田。"
                },
                "daily_guide": [
                    "宜保持内心平静",
                    "宜关注身边美好"
                ],
                "fengshui_focus": "面向光明的方向",
                "ritual_hint": "深呼吸，感受当下的美好",
                "element_balance": {
                    "wood": 0.5, "fire": 0.5, "earth": 0.5, "metal": 0.5, "water": 0.5
                }
            },
            "ink_reading": {
                "stroke_impression": "笔触温和，显示内心的平静状态",
                "symbolic_keywords": ["温和", "平静"],
                "ink_metrics": {
                    "stroke_count": 0,
                    "dominant_quadrant": "center",
                    "pressure_tendency": "steady"
                }
            },
            "context_insights": {
                "session_time": session_time,
                "season_hint": season_hint,
                "visit_pattern": "心象之旅",
                "historical_keywords": []
            },
            "blessing_stream": [
                "心想事成",
                "平安喜乐",
                "一路顺风",
                "温暖相伴"
            ],
            "art_direction": {
                "image_prompt": "温和的自然光影，水彩风格",
                "palette": ["#dfe6e9", "#b2bec3", "#74b9ff"],
                "animation_hint": "轻柔的光影变化"
            },
            "culture_note": "灵感源于传统文化智慧，不作吉凶断言，请以现代视角理解。"
        }
