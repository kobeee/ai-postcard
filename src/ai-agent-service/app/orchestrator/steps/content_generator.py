import logging
import json
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ContentGenerator:
    """内容生成器 - 第2步：生成心象签祈福文案和解读内容"""
    
    def __init__(self):
        # 文本生成使用 Gemini
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context):
        """基于概念生成心象签祈福文案和解读内容"""
        task = context["task"]
        concept = context["results"]["concept"]
        selected_charm = context["results"].get("selected_charm_style", {})
        
        self.logger.info(f"✍️ 开始生成心象签文案: {task.get('task_id')}")
        
        # 提取上下文信息
        ink_metrics = task.get('drawing_data', {}).get('analysis', {})
        user_input = task.get('user_input', '')
        quiz_answers = task.get('quiz_answers', [])
        
        # 分析问答数据
        quiz_insights = self._generate_quiz_insights(quiz_answers)
        
        # 解析概念数据
        concept_data = {}
        try:
            if isinstance(concept, str) and concept.strip().startswith('{'):
                concept_data = json.loads(concept)
        except json.JSONDecodeError:
            pass
        
        # 构建心象签文案生成提示词
        content_prompt = f"""
你是一位心象签文案师，专门为用户创作温柔而有力量的祈福文案和解读内容。

创意概念：{concept}
用户输入：{user_input}
自然意象：{concept_data.get('natural_scene', '晨光照进窗')}
情绪基调：{concept_data.get('emotion_tone', '平静')}
绘画印象：{ink_metrics.get('drawing_description', '平和的笔触')}

问答洞察：{quiz_insights.get('summary', '心境平和')}
情绪倾向：{quiz_insights.get('emotion_vector', {})}
行动偏好：{quiz_insights.get('action_focus', [])}

选择签体：{selected_charm.get('name', '莲花圆牌')}
签体风格：{selected_charm.get('note', '平和雅致')}

请基于心象签的理念，结合绘画印象和问答洞察，生成以下内容：

1. 祈福短句（affirmation）：8-14字的正向祈福，温柔有力量，结合quiz_insights
2. 笔触印象（stroke_impression）：从绘画特征感受到的情绪状态，25-40字
3. 象征关键词（symbolic_keywords）：3个体现内在情绪的关键词
4. 生活指引（daily_guide）：2-3条温和的生活建议，每条15-25字，与问答洞察呼应

文案风格要求：
- 温柔、日常、半诗意，避免命令式/玄学口吻
- 现代语汇，非吉凶断言的定位
- 与自然意象和签体风格形成呼应
- 给人以安慰和前进的力量
- 结合quiz_insights，让内容更贴合用户的真实心境

请以JSON格式返回：
{{
    "affirmation": "愿所盼皆有回应",
    "stroke_impression": "线条舒展，显示你内心正在寻找平衡，笔触时缓时急，像是思绪在整理", 
    "symbolic_keywords": ["流动", "平衡", "柔和"],
    "daily_guide": [
        "宜整理书桌，让思绪重新落座",
        "宜早点休息，守住夜晚的宁静"
    ]
}}

注意：
- affirmation要结合quiz_insights的emotion_vector，贴合用户的真实需要
- stroke_impression要结合ink_metrics的真实数据，更具体和生动
- daily_guide要与action_focus呼应，提供实用的生活指引
- 所有内容都要与选择的签体风格保持一致
"""
        
        try:
            # 调用Gemini文本生成
            content = await self.provider.generate_text(
                prompt=content_prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            context["results"]["content"] = content
            context["results"]["quiz_insights"] = quiz_insights
            
            self.logger.info(f"✅ 文案生成完成: {len(content)} 字符")
            self.logger.info(f"🧠 问答洞察: {quiz_insights.get('summary', '心境平和')}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 文案生成失败: {e}")
            # 返回默认文案
            context["results"]["content"] = self._get_default_content(task)
            context["results"]["quiz_insights"] = {
                "summary": "心境平和，内心安宁",
                "emotion_vector": {"calm": 0.7},
                "action_focus": ["保持平静"]
            }
            return context
    
    def _generate_quiz_insights(self, quiz_answers):
        """基于问答生成深度洞察"""
        if not quiz_answers:
            return {
                "summary": "心境平和，内心安宁",
                "emotion_vector": {"calm": 0.7, "confidence": 0.6},
                "action_focus": ["保持平静"]
            }
        
        try:
            # 分析问答模式，生成更精准的洞察
            insights = {
                "needs_rest": False,
                "needs_connection": False,
                "needs_growth": False,
                "stress_level": "low",
                "clarity_level": "high"
            }
            
            # 分析具体答案模式
            for answer in quiz_answers:
                option_id = answer.get('option_id', '')
                
                # 分析特定问答模式
                if 'rest' in option_id or 'sleep' in option_id or 'tired' in option_id:
                    insights["needs_rest"] = True
                if 'companion' in option_id or 'talk' in option_id or 'together' in option_id:
                    insights["needs_connection"] = True
                if 'growth' in option_id or 'learn' in option_id or 'create' in option_id:
                    insights["needs_growth"] = True
                if 'pressure' in option_id or 'stress' in option_id or 'overwhelmed' in option_id:
                    insights["stress_level"] = "high"
                if 'confused' in option_id or 'fog' in option_id or 'unclear' in option_id:
                    insights["clarity_level"] = "low"
            
            # 生成洞察总结
            summary_parts = []
            emotion_vector = {}
            action_focus = []
            
            if insights["needs_rest"]:
                summary_parts.append("需要给自己一些休息时间")
                emotion_vector["tired"] = 0.7
                action_focus.append("适度休息")
                
            if insights["needs_connection"]:
                summary_parts.append("渴望与他人建立更深的连接")
                emotion_vector["longing"] = 0.6
                action_focus.append("主动交流")
                
            if insights["needs_growth"]:
                summary_parts.append("内心有着成长的渴望")
                emotion_vector["motivation"] = 0.8
                action_focus.append("学习成长")
                
            if insights["stress_level"] == "high":
                summary_parts.append("正在经历一些压力")
                emotion_vector["stress"] = 0.7
                action_focus.append("压力管理")
            
            if insights["clarity_level"] == "low":
                summary_parts.append("对某些事情感到迷茫")
                emotion_vector["confusion"] = 0.6
                action_focus.append("清晰思考")
            
            # 如果没有特殊模式，返回积极的默认状态
            if not summary_parts:
                summary = "你正在维持着一种平衡的状态"
                emotion_vector = {"balance": 0.8, "calm": 0.7}
                action_focus = ["继续保持"]
            else:
                summary = "、".join(summary_parts)
            
            return {
                "summary": summary,
                "emotion_vector": emotion_vector,
                "action_focus": action_focus
            }
            
        except Exception as e:
            self.logger.error(f"❌ 生成问答洞察失败: {e}")
            return {
                "summary": "心境平和，内心安宁",
                "emotion_vector": {"calm": 0.7, "confidence": 0.6},
                "action_focus": ["保持平静"]
            }
    
    def _get_default_content(self, task):
        """获取默认心象签文案（兜底方案）"""
        return f"""{{
    "affirmation": "愿你的努力皆被温柔回应",
    "stroke_impression": "笔触柔软，显示你内心有一块柔软区域正在被温柔地触碰，这是心灵治愈的开始",
    "symbolic_keywords": ["柔和", "治愈", "成长"],
    "daily_guide": [
        "宜整理桌面，给心绪留出呼吸的空间",
        "宜尝试5分钟冥想，让自己与内心连接"
    ]
}}"""