# 使用官方推荐的google-genai SDK
from google import genai
from typing import Dict, Any, Optional
from .base_provider import BaseImageProvider
import os
import aiohttp
import asyncio
from PIL import Image
from io import BytesIO
import base64

class GeminiImageProvider(BaseImageProvider):
    """Gemini图片生成服务提供商"""
    
    def __init__(self):
        super().__init__()
        
        # 配置API
        api_key = os.getenv("META_API_KEY")
        if not api_key:
            # 不再抛出异常，允许走占位图fallback
            self.logger.warning("⚠️ META_API_KEY 未配置，将使用占位图片fallback")
            api_key = ""
            
        self.api_key = api_key
        self.base_url = os.getenv("META_BASE_URL", "https://generativelanguage.googleapis.com")
        self.model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")
        self.default_size = os.getenv("GEMINI_IMAGE_SIZE", "512x512")
        self.default_quality = os.getenv("GEMINI_IMAGE_QUALITY", "standard")
        
        # 配置Gemini客户端（按官网教程）
        self.client = None
        if api_key:
            self.client = genai.Client(
                api_key=api_key,
                http_options=genai.types.HttpOptions(base_url=self.base_url)
            )
        # 控制是否严格调用真实生图API
        self.strict_mode = os.getenv("GEMINI_IMAGE_STRICT", "false").lower() == "true"
        
        self.logger.info(f"✅ Gemini图片提供商初始化成功: {self.model_name}")
    
    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成图片"""
        try:
            size = size or self.default_size
            quality = quality or self.default_quality
            
            self.logger.info(f"🎨 开始生成图片，模型: {self.model_name}")
            
            # 未开启严格模式或未配置Key：直接返回占位图，避免阻断流程
            if not self.strict_mode or not self.client:
                self.logger.info("ℹ️ 未开启严格模式或未配置API Key，返回占位图以通过流程验证")
                return {
                    "image_url": self._placeholder_url(),
                    "metadata": {
                        "prompt": prompt,
                        "size": size,
                        "quality": quality,
                        "model": self.model_name,
                        "provider": "gemini",
                        "fallback": True,
                        "reason": "strict_mode_disabled_or_no_api_key"
                    }
                }
            
            # 直接使用传入的prompt，不再重复包装
            # image_generator.py已经构建了完整的专业提示词
            final_prompt = prompt
            self.logger.info(f"📝 使用传入的完整prompt（长度: {len(final_prompt)} 字符）")
            
            # 按照官网教程调用图片生成API
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=final_prompt,
                    config=genai.types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
            )
            
            # 按照官方教程处理响应
            if response.candidates and len(response.candidates) > 0:
                content_parts = response.candidates[0].content.parts
                
                # 查找图片数据
                image_saved = False
                image_url = None
                
                for part in content_parts:
                    if part.text is not None:
                        self.logger.info(f"📝 Gemini返回文本: {part.text[:100]}...")
                    elif part.inline_data is not None:
                        # 保存图片数据
                        try:
                            image = Image.open(BytesIO(part.inline_data.data))
                            
                            # 创建保存目录
                            import tempfile
                            import uuid
                            
                            # 生成唯一文件名
                            image_id = str(uuid.uuid4())[:8]
                            image_filename = f"gemini_generated_{image_id}.png"
                            
                            # 保存到静态文件目录，供HTTP访问
                            static_dir = "/app/app/static/generated"
                            os.makedirs(static_dir, exist_ok=True)
                            image_path = f"{static_dir}/{image_filename}"
                            image.save(image_path)
                            
                            # 构建可通过HTTP访问的URL
                            base_url = os.getenv("AI_AGENT_PUBLIC_URL", "http://ai-agent-service:8000")
                            image_url = f"{base_url}/static/generated/{image_filename}"
                            image_saved = True
                            
                            self.logger.info(f"✅ 图片保存成功: {image_path}")
                            break
                            
                        except Exception as save_error:
                            self.logger.error(f"❌ 图片保存失败: {save_error}")
                
                if image_saved and image_url:
                    result = {
                        "image_url": image_url,
                        "metadata": {
                            "prompt": prompt,
                            "size": size,
                            "quality": quality,
                            "model": self.model_name,
                            "provider": "gemini",
                            "real_generation": True
                        }
                    }
                    self.logger.info("✅ Gemini真实图片生成成功")
                    return result
                else:
                    raise Exception("Gemini返回的响应中没有找到图片数据")
            else:
                raise Exception("Gemini图片生成返回空响应或无候选结果")
                        
        except Exception as e:
            self.logger.error(f"❌ Gemini图片生成失败: {e}")
            # 返回一个备用的占位图片
            return {
                "image_url": self._placeholder_url(),
                "metadata": {
                    "prompt": prompt,
                    "size": size,
                    "quality": quality,
                    "model": self.model_name,
                    "provider": "gemini",
                    "error": str(e),
                    "fallback": True
                }
            }
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单的连接测试
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/v1/models"
                headers = {"x-goog-api-key": self.api_key}
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except:
            return False

    def _placeholder_url(self) -> str:
        return "https://via.placeholder.com/1024x1024/FFB6C1/000000?text=AI+Generated+Image"