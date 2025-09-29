import logging
import json
import os
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ImageGenerator:
    """图片生成器 - 第3步：基于心象签概念生成自然祝福图"""
    
    def __init__(self):
        # 根据环境变量选择图片生成provider
        provider_type = os.getenv("IMAGE_PROVIDER_TYPE", "gemini")
        self.provider = ProviderFactory.create_image_provider(provider_type)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"✅ 图片生成器初始化，使用provider: {provider_type}")
    
    async def execute(self, context):
        """基于心象签数据生成自然祝福图"""
        task = context["task"]
        structured_data = context["results"].get("structured_data", {})
        
        self.logger.info(f"🎨 开始生成心象签自然祝福图: {task.get('task_id')}")
        
        # 从结构化数据中提取art_direction
        art_direction = {}
        if isinstance(structured_data, dict):
            art_direction = structured_data.get("art_direction", {})
        elif isinstance(structured_data, str):
            try:
                parsed_data = json.loads(structured_data)
                art_direction = parsed_data.get("art_direction", {})
            except json.JSONDecodeError:
                pass
        
        # 提取图片生成所需信息
        image_prompt_base = art_direction.get("image_prompt", "晨曦与薄雾的抽象水彩")
        palette = art_direction.get("palette", ["#f5e6cc", "#d9c4f2", "#9DE0AD"])
        animation_hint = art_direction.get("animation_hint", "从模糊到清晰的光晕扩散")
        
        # 从oracle_theme中获取自然意象
        oracle_theme = structured_data.get("oracle_theme", {})
        natural_scene = oracle_theme.get("title", "晨光照进窗") if isinstance(oracle_theme, dict) else "晨光照进窗"
        
        # 构建心象签自然祝福图生成提示词（完整专业版本）
        image_prompt = f"""Create a high-quality watercolor background image for a heart oracle postcard:

Scene: "{natural_scene}"
Color Palette: {palette[0]}, {palette[1]}, {palette[2]} 
Lighting Effect: {animation_hint}

Style Requirements:
- Abstract watercolor technique with soft, flowing edges
- Harmonious and artistic color blending
- Atmospheric and elegant composition
- Suitable for text overlay placement
- Positive and peaceful mood
- Resolution: 1024x1024 pixels

Important Constraints:
- NO TEXT, NO WORDS, NO LETTERS, NO CHARACTERS of any kind
- NO symbols, logos, or written content
- Focus purely on visual elements: landscapes, nature, abstract patterns
- Create pure artistic background without textual elements

Generate a beautiful, serene watercolor background that captures the essence of "{natural_scene}" using the specified colors and lighting."""
        
        try:
            # 调用Gemini图片生成
            image_result = await self.provider.generate_image(
                prompt=image_prompt,
                size="1024x1024",
                quality="standard"
            )
            
            context["results"]["image_url"] = image_result["image_url"]
            
            # 增强metadata，包含心象签信息
            metadata = image_result.get("metadata", {})
            metadata.update({
                "purpose": "natural_blessing",
                "oracle_scene": natural_scene,
                "palette": palette,
                "animation_hint": animation_hint,
                "art_style": "abstract_watercolor"
            })
            context["results"]["image_metadata"] = metadata
            
            self.logger.info(f"✅ 心象签自然祝福图生成完成: {image_result['image_url']}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 心象签祝福图生成失败: {e}")
            # 返回默认祝福图
            context["results"]["image_url"] = self._get_default_blessing_image()
            context["results"]["image_metadata"] = {
                "fallback": True,
                "purpose": "natural_blessing",
                "oracle_scene": natural_scene,
                "error": str(e)
            }
            return context
    
    def _get_default_blessing_image(self):
        """获取默认心象签祝福图（兜底方案）"""
        # 返回一个符合心象签理念的默认图片
        # 这里可以是项目中预设的自然风景抽象图
        return "https://via.placeholder.com/1024x1024/F5E6CC/D9C4F2?text=Natural+Blessing"
    
    def _get_default_image(self):
        """获取默认图片（兼容性保留）"""
        return self._get_default_blessing_image()