import logging
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ConceptGenerator:
    """概念生成器 - 第1步：基于用户需求生成创意概念"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context):
        """生成明信片概念和创意方向"""
        task = context["task"]
        
        self.logger.info(f"🎯 开始生成概念: {task.get('task_id')}")
        
        # 构建概念生成提示词
        concept_prompt = f"""
请根据用户需求生成一个创意明信片概念：

用户需求：{task.get('user_input')}
风格偏好：{task.get('style', '不限')}
主题类型：{task.get('theme', '不限')}

请生成以下内容：
1. 主题概念：明信片的核心主题和情感表达（1-2句话）
2. 视觉风格：色彩搭配、构图风格、艺术表现形式的建议
3. 文案方向：文字内容的情感基调和表达方式
4. 目标场景：适合的使用场景和传达的情感

请以JSON格式返回，包含以下字段：
{{
    "主题概念": "...",
    "视觉风格": "...",
    "文案方向": "...",
    "目标场景": "..."
}}
"""
        
        try:
            # 调用Gemini文本生成
            concept = await self.provider.generate_text(
                prompt=concept_prompt,
                max_tokens=1024,
                temperature=0.8
            )
            
            context["results"]["concept"] = concept
            self.logger.info(f"✅ 概念生成完成: {len(concept)} 字符")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 概念生成失败: {e}")
            # 返回默认概念
            context["results"]["concept"] = self._get_default_concept(task)
            return context
    
    def _get_default_concept(self, task):
        """获取默认概念（兜底方案）"""
        return f"""{{
    "主题概念": "基于'{task.get('user_input')}'的温馨明信片设计",
    "视觉风格": "简洁现代，色彩温和，适合表达真挚情感",
    "文案方向": "简短有力，情感真挚，易于理解和传达",
    "目标场景": "适合在特殊时刻向重要的人传达心意"
}}"""