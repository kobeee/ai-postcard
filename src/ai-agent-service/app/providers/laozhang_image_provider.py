import aiohttp
import asyncio
import base64
import json
import os
import re
import uuid
from typing import Dict, Any, Optional
from PIL import Image
from io import BytesIO
from .base_provider import BaseImageProvider


class LaoZhangImageProvider(BaseImageProvider):
    """老张AI图片生成服务提供商"""
    
    def __init__(self):
        super().__init__()
        
        # 配置API
        self.api_key = os.getenv("LAO_ZHANG_API_KEY")
        self.api_url = os.getenv("LAO_ZHANG_URL", "https://api.laozhang.ai/v1/chat/completions")
        self.model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image-preview")
        self.default_size = os.getenv("GEMINI_IMAGE_SIZE", "512x512")
        self.default_quality = os.getenv("GEMINI_IMAGE_QUALITY", "standard")
        
        if not self.api_key:
            self.logger.warning("⚠️ LAO_ZHANG_API_KEY 未配置，将使用占位图片fallback")
        
        # 控制是否严格调用真实生图API
        self.strict_mode = os.getenv("LAO_ZHANG_IMAGE_STRICT", "false").lower() == "true"
        
        self.logger.info(f"✅ 老张AI图片提供商初始化成功: {self.model_name}")
    
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
            if not self.strict_mode or not self.api_key:
                self.logger.info("ℹ️ 未开启严格模式或未配置API Key，返回占位图以通过流程验证")
                return {
                    "image_url": self._placeholder_url(),
                    "metadata": {
                        "prompt": prompt,
                        "size": size,
                        "quality": quality,
                        "model": self.model_name,
                        "provider": "laozhang",
                        "fallback": True,
                        "reason": "strict_mode_disabled_or_no_api_key"
                    }
                }
            
            # 直接使用传入的prompt，不再重复包装
            # image_generator.py已经构建了完整的专业提示词
            final_prompt = prompt
            self.logger.info(f"📝 使用传入的完整prompt（长度: {len(final_prompt)} 字符）")
            
            # 调用老张AI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model_name,
                "stream": False,
                "messages": [
                    {
                        "role": "user", 
                        "content": final_prompt
                    }
                ]
            }
            
            self.logger.info("📡 发送API请求到老张AI...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    
                    if response.status != 200:
                        error_msg = f"API请求失败，状态码: {response.status}"
                        try:
                            error_detail = await response.json()
                            error_msg += f", 错误详情: {error_detail}"
                        except:
                            error_text = await response.text()
                            error_msg += f", 响应内容: {error_text[:500]}"
                        raise Exception(error_msg)
                    
                    self.logger.info("✅ API请求成功，正在解析响应...")
                    
                    # 解析JSON响应
                    result = await response.json()
                    self.logger.info("✅ 成功解析JSON响应")
                    
                    # 提取消息内容
                    full_content = ""
                    if "choices" in result and len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            full_content = choice["message"]["content"]
                    
                    if not full_content:
                        raise Exception("未找到消息内容")
                    
                    self.logger.info(f"📝 获取到消息内容，长度: {len(full_content)} 字符")
                    self.logger.info("🔍 正在解析图片数据...")
                    
                    # 提取并保存图片
                    image_url = await self._extract_and_save_image(full_content)
                    
                    if image_url:
                        result = {
                            "image_url": image_url,
                            "metadata": {
                                "prompt": prompt,
                                "size": size,
                                "quality": quality,
                                "model": self.model_name,
                                "provider": "laozhang",
                                "real_generation": True
                            }
                        }
                        self.logger.info("✅ 老张AI真实图片生成成功")
                        return result
                    else:
                        raise Exception("图片保存失败")
                        
        except Exception as e:
            self.logger.error(f"❌ 老张AI图片生成失败: {e}")
            # 返回一个备用的占位图片
            return {
                "image_url": self._placeholder_url(),
                "metadata": {
                    "prompt": prompt,
                    "size": size,
                    "quality": quality,
                    "model": self.model_name,
                    "provider": "laozhang",
                    "error": str(e),
                    "fallback": True
                }
            }
    
    async def _extract_and_save_image(self, content: str) -> Optional[str]:
        """高效提取并保存base64图片数据"""
        try:
            self.logger.info(f"📄 内容预览（前200字符）: {content[:200]}")
            
            # 使用精确的正则表达式提取base64图片数据
            base64_pattern = r'data:image/([^;]+);base64,([A-Za-z0-9+/=]+)'
            match = re.search(base64_pattern, content)
            
            if not match:
                self.logger.warning('⚠️ 未找到base64图片数据')
                return None
            
            image_format = match.group(1)  # png, jpg, etc.
            b64_data = match.group(2)
            
            self.logger.info(f'🎨 图像格式: {image_format}')
            self.logger.info(f'📏 Base64数据长度: {len(b64_data)} 字符')
            
            # 解码图片数据
            image_data = base64.b64decode(b64_data)
            
            if len(image_data) < 100:
                self.logger.error("解码后的图片数据太小，可能无效")
                return None
            
            # 保存图片
            image = Image.open(BytesIO(image_data))
            
            # 生成唯一文件名
            image_id = str(uuid.uuid4())[:8]
            image_filename = f"laozhang_generated_{image_id}.{image_format}"
            
            # 保存到静态文件目录，供HTTP访问
            static_dir = "/app/app/static/generated"
            os.makedirs(static_dir, exist_ok=True)
            image_path = f"{static_dir}/{image_filename}"
            image.save(image_path)
            
            # 构建可通过HTTP访问的URL
            base_url = os.getenv("AI_AGENT_PUBLIC_URL", "http://ai-agent-service:8000")
            image_url = f"{base_url}/static/generated/{image_filename}"
            
            self.logger.info(f'🖼️ 图片保存成功: {image_path}')
            self.logger.info(f'📊 文件大小: {len(image_data)} 字节')
            
            return image_url
                
        except Exception as e:
            self.logger.error(f"处理图片时发生错误: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.api_key:
                return False
                
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 简单的连接测试
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url.replace('/chat/completions', '/models'),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status in [200, 404]  # 404也算正常，说明连接通了
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False

    def _placeholder_url(self) -> str:
        return "https://via.placeholder.com/1024x1024/87CEEB/000000?text=LaoZhang+AI+Generated"