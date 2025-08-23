import logging
import json
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ImageGenerator:
    """图片生成器 - 第3步：基于概念和内容生成明信片配图"""
    
    def __init__(self):
        # 图片生成使用 Gemini
        self.provider = ProviderFactory.create_image_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, context):
        """基于概念和内容生成明信片配图"""
        task = context["task"]
        concept = context["results"]["concept"]
        content = context["results"]["content"]
        
        self.logger.info(f"🎨 开始生成图片: {task.get('task_id')}")
        
        # 解析概念中的视觉风格信息
        try:
            if isinstance(concept, str) and concept.strip().startswith('{'):
                concept_data = json.loads(concept)
                visual_style = concept_data.get("视觉风格", "温馨、简洁、现代风格")
            else:
                visual_style = "温馨、简洁、现代风格"
        except json.JSONDecodeError:
            visual_style = "温馨、简洁、现代风格"
        
        # 解析内容中的主题信息
        try:
            if isinstance(content, str) and content.strip().startswith('{'):
                content_data = json.loads(content)
                main_theme = content_data.get("主标题", "") + " " + content_data.get("副标题", "")
            else:
                main_theme = task.get('user_input', '美好祝愿')
        except json.JSONDecodeError:
            main_theme = task.get('user_input', '美好祝愿')
        
        # 构建图片生成提示词
        image_prompt = f"""
为明信片生成配图，基于以下要求：

主题内容：{main_theme}
视觉风格：{visual_style}
用户需求：{task.get('user_input')}

设计要求：
- 高质量插画风格或水彩风格
- 色彩和谐，适合明信片使用
- 构图简洁，留有足够的文字摆放空间
- 避免过于复杂的细节，确保在小尺寸下也清晰可见
- 情感表达积极正面，符合明信片的温馨氛围
- 适合印刷，色彩饱和度适中

风格参考：
- 如果是节日主题，加入相应的节日元素
- 如果是情感表达，使用温暖的色调
- 如果是生活场景，展现美好的日常瞬间

请生成一张符合以上要求的精美明信片背景图。
"""
        
        try:
            # 调用Gemini图片生成
            image_result = await self.provider.generate_image(
                prompt=image_prompt,
                size="1024x1024",
                quality="standard"
            )
            
            context["results"]["image_url"] = image_result["image_url"]
            context["results"]["image_metadata"] = image_result["metadata"]
            
            self.logger.info(f"✅ 图片生成完成: {image_result['image_url']}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 图片生成失败: {e}")
            # 返回默认图片
            context["results"]["image_url"] = self._get_default_image()
            context["results"]["image_metadata"] = {
                "fallback": True,
                "error": str(e)
            }
            return context
    
    def _get_default_image(self):
        """获取默认图片（兜底方案）"""
        # 返回一个美观的占位图片
        return "https://via.placeholder.com/1024x1024/FFE4E1/8B4513?text=AI+Generated+Postcard"