import logging
import json
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ContentGenerator:
    """内容生成器 - 第2步：基于概念生成明信片文案"""
    
    def __init__(self):
        self.provider = ProviderFactory.create_text_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context):
        """基于概念生成明信片文案内容"""
        task = context["task"]
        concept = context["results"]["concept"]
        
        self.logger.info(f"✍️ 开始生成文案: {task.get('task_id')}")
        
        # 构建内容生成提示词
        content_prompt = f"""
基于以下创意概念，为明信片生成具体的文案内容：

创意概念：
{concept}

用户原始需求：{task.get('user_input')}

请生成适合明信片的文案内容，包括：

1. 主标题：简洁有力的核心文字（5-10字）
2. 副标题：补充说明或情感表达（8-15字，可选）
3. 正文内容：详细的祝福或表达内容（20-50字）
4. 署名建议：适合的落款方式（3-8字，如"致亲爱的你"、"来自朋友"等）

要求：
- 符合中文表达习惯，语言自然流畅
- 情感真挚，不要过于华丽或做作
- 字数适中，适合明信片展示
- 考虑目标受众和使用场景

请以JSON格式返回，包含以下字段：
{{
    "主标题": "...",
    "副标题": "...",
    "正文内容": "...",
    "署名建议": "..."
}}
"""
        
        try:
            # 调用Gemini文本生成
            content = await self.provider.generate_text(
                prompt=content_prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            context["results"]["content"] = content
            self.logger.info(f"✅ 文案生成完成: {len(content)} 字符")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 文案生成失败: {e}")
            # 返回默认文案
            context["results"]["content"] = self._get_default_content(task)
            return context
    
    def _get_default_content(self, task):
        """获取默认文案（兜底方案）"""
        user_input = task.get('user_input', '美好祝愿')
        
        return f"""{{
    "主标题": "温馨祝福",
    "副标题": "来自心底的真诚",
    "正文内容": "愿{user_input}能够带给你温暖与快乐，每一天都充满阳光与希望。",
    "署名建议": "致亲爱的你"
}}"""