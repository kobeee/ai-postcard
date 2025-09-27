import logging
import json
from ...providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class ImageGenerator:
    """图片生成器 - 第3步：基于心象签概念生成自然祝福图"""
    
    def __init__(self):
        # 图片生成使用 Gemini
        self.provider = ProviderFactory.create_image_provider("gemini")
        self.logger = logging.getLogger(self.__class__.__name__)
    
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
        
        # 构建心象签自然祝福图生成提示词
        image_prompt = f"""
为心象签生成自然祝福图，基于以下心象意境：

核心意象：{natural_scene}
艺术指导：{image_prompt_base}
色彩灵感：{palette}
动画提示：{animation_hint}

设计要求：
- 专注于自然奇景的抽象艺术表现（水彩、油画或插画风格）
- 体现"{natural_scene}"这一自然意象的核心美感
- 使用指定色彩{palette}作为主色调，营造和谐氛围
- 抽象而不失意境，让人感受到自然的美好与祝福
- 适合在小程序webview中作为背景展示
- 考虑{animation_hint}的视觉效果需求

心象签核心理念：
- 通过自然现象传达内在情感和祝福
- 画面要有疗愈感和温暖感
- 避免过于具象，保持诗意的抽象美感
- 色彩柔和，适合冥想和反思

严格约束条件：
- 🚫 绝对禁止任何文字、字母、数字、符号或宗教标识
- 🚫 不能有任何可识别的文本内容或类文字图案
- 🚫 避免人工建筑物、具体物品、人物形象
- ✅ 纯自然元素：光影、云彩、水流、植物、山川、天空等
- ✅ 通过色彩、光影、纹理传达自然的祝福力量

艺术风格：
- 现代抽象水彩/油画风格
- 色彩过渡自然，层次丰富
- 光影变化体现"{animation_hint}"的动态美感
- 整体画面传达宁静、祝福、希望的情感

请生成一张体现"{natural_scene}"意境的纯自然抽象祝福图。
"""
        
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